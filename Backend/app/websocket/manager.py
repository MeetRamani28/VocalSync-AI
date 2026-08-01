import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import (
    scrub_pii,
    PromptInjectionDetectedError,
    PayloadTooLargeError,
    SecurityViolationError,
)
from app.db.client import get_db
from app.schemas.call import (
    WSMessage,
    WSMessageType,
    CallStatus,
    Sentiment,
    TranscriptMessage,
)
from app.schemas.lead import LeadExtractionToolSchema, LeadStatus
from app.services.stt import stt_service
from app.services.llm import llm_service
from app.services.tts import tts_service

logger = logging.getLogger("vocalsync.websocket")

SENTENCE_BOUNDARY_REGEX = re.compile(r"([.?!])\s*")


class VoiceSessionState:
    """
    In-memory state container for an active voice call session.
    """
    def __init__(self, call_id: str, websocket: WebSocket):
        self.call_id = call_id
        self.websocket = websocket
        self.history: List[Dict[str, str]] = []
        self.status = CallStatus.IN_PROGRESS
        self.start_time = datetime.now(timezone.utc)
        self.latest_sentiment = Sentiment.NEUTRAL
        self.lead_id: Optional[str] = None


class WebSocketConnectionManager:
    """
    Enterprise real-time bidirectional WebSocket manager.
    Orchestrates STT -> LLM -> TTS pipelines and OWASP LLM Top 10 security guardrails.
    """
    def __init__(self):
        self.active_sessions: Dict[str, VoiceSessionState] = {}

    async def connect(self, websocket: WebSocket, call_id: str) -> VoiceSessionState:
        """
        Accepts WebSocket handshake and initializes a secure voice session.
        """
        await websocket.accept()
        session = VoiceSessionState(call_id=call_id, websocket=websocket)
        self.active_sessions[call_id] = session

        logger.info(f"WebSocket session established: [Call ID: {call_id}]")
        
        await self.send_json(
            websocket,
            WSMessage(
                event=WSMessageType.AGENT_STATE,
                data={"status": "connected", "call_id": call_id, "message": "Voice engine ready"}
            )
        )
        return session

    async def disconnect(self, call_id: str) -> None:
        """
        Cleans up in-memory session state and finalizes database call logs.
        """
        session = self.active_sessions.pop(call_id, None)
        if session:
            logger.info(f"WebSocket session closed: [Call ID: {call_id}]")
            asyncio.create_task(self._finalize_call_log(session))

    async def send_json(self, websocket: WebSocket, message: WSMessage) -> None:
        """
        Sends a Pydantic-validated JSON payload over the WebSocket connection.
        """
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to transmit WebSocket JSON message: {e}")

    async def send_audio_bytes(self, websocket: WebSocket, audio_data: bytes) -> None:
        """
        Sends binary audio PCM/MP3 chunks to the React frontend audio player.
        """
        try:
            await websocket.send_bytes(audio_data)
        except Exception as e:
            logger.error(f"Failed to transmit binary audio payload: {e}")

    async def handle_audio_stream(self, call_id: str, audio_bytes: bytes) -> None:
        """
        Core sub-second orchestration loop:
        1. STT Transcription + OWASP LLM01 Sanitization
        2. LLM Token Streaming + Sentence-Boundary Chunking
        3. Edge-TTS Audio Generation -> Immediate Client Playback
        4. Async Background Lead Extraction + PII-Scrubbed MongoDB Persistence
        """
        session = self.active_sessions.get(call_id)
        if not session:
            logger.warning(f"Audio received for untracked session: {call_id}")
            return

        try:
            transcript = await stt_service.transcribe_audio_buffer(audio_bytes)
            if not transcript:
                return  

            session.history.append({"role": "user", "content": transcript})

            await self.send_json(
                session.websocket,
                WSMessage(
                    event=WSMessageType.TRANSCRIPT_UPDATE,
                    data={"role": "user", "content": transcript, "sentiment": session.latest_sentiment}
                )
            )

            full_assistant_response = ""
            sentence_buffer = ""

            await self.send_json(
                session.websocket,
                WSMessage(
                    event=WSMessageType.AGENT_STATE,
                    data={"status": "speaking", "call_id": call_id}
                )
            )

            async for token in llm_service.generate_voice_stream(session.history):
                full_assistant_response += token
                sentence_buffer += token

                await self.send_json(
                    session.websocket,
                    WSMessage(
                        event=WSMessageType.TEXT_TOKEN,
                        data={"token": token}
                    )
                )

                if SENTENCE_BOUNDARY_REGEX.search(sentence_buffer):
                    await self._stream_tts_sentence(session.websocket, sentence_buffer.strip())
                    sentence_buffer = ""

            if sentence_buffer.strip():
                await self._stream_tts_sentence(session.websocket, sentence_buffer.strip())

            session.history.append({"role": "assistant", "content": full_assistant_response})

            await self.send_json(
                session.websocket,
                WSMessage(
                    event=WSMessageType.TRANSCRIPT_UPDATE,
                    data={"role": "assistant", "content": full_assistant_response, "sentiment": "Neutral"}
                )
            )

            asyncio.create_task(self._async_post_turn_processing(session))

        except PromptInjectionDetectedError as pie:
            logger.error(f"OWASP LLM01 Prompt Injection intercepted: {pie}")
            await self._handle_security_rejection(session, "I am a VocalSync AI assistant and can only discuss sales qualification and product details.")
        
        except PayloadTooLargeError as ptle:
            logger.error(f"Input payload exceeded security limits: {ptle}")
            await self._handle_security_rejection(session, "Your audio transmission was too long. Please keep questions concise.")

        except SecurityViolationError as sve:
            logger.error(f"Security violation caught in stream: {sve}")
            await self._handle_security_rejection(session, "A security policy violation was detected. Continuing conversation.")

        except Exception as e:
            logger.critical(f"Unhandled exception in WebSocket audio stream loop: {e}", exc_info=True)
            await self.send_json(
                session.websocket,
                WSMessage(
                    event=WSMessageType.ERROR,
                    data={"error": "An internal voice processing error occurred. Please try again."}
                )
            )

    async def _stream_tts_sentence(self, websocket: WebSocket, sentence: str) -> None:
        """
        Synthesizes a single sentence into Edge-TTS audio bytes and sends chunks
        to the WebSocket immediately.
        """
        if not sentence:
            return
        try:
            async for audio_chunk in tts_service.stream_audio_from_text(sentence):
                await self.send_audio_bytes(websocket, audio_chunk)
        except Exception as e:
            logger.error(f"Error streaming TTS sentence chunk: {e}")

    async def _handle_security_rejection(self, session: VoiceSessionState, safe_response: str) -> None:
        """
        Graceful recovery for OWASP security violations. Sends a safe voice response
        instead of disconnecting or crashing the WebSocket.
        """
        session.history.append({"role": "assistant", "content": safe_response})
        await self.send_json(
            session.websocket,
            WSMessage(
                event=WSMessageType.TRANSCRIPT_UPDATE,
                data={"role": "assistant", "content": safe_response, "sentiment": "Neutral"}
            )
        )
        await self._stream_tts_sentence(session.websocket, safe_response)

    async def _async_post_turn_processing(self, session: VoiceSessionState) -> None:
        """
        Background task: Evaluates sentiment, extracts structured CRM lead data,
        scrubs PII (OWASP LLM06), and writes non-blocking updates to MongoDB Atlas.
        """
        try:
            sentiment, lead_schema = await llm_service.analyze_sentiment_and_extract_lead(session.history)
            session.latest_sentiment = sentiment

            db = get_db()

            scrubbed_transcripts = []
            for msg in session.history:
                scrubbed_transcripts.append(
                    TranscriptMessage(
                        role=msg["role"],
                        content=scrub_pii(msg["content"]),
                        sentiment=sentiment if msg["role"] == "user" else Sentiment.NEUTRAL
                    ).model_dump()
                )

            call_update_payload = {
                "$set": {
                    "call_id": session.call_id,
                    "status": CallStatus.IN_PROGRESS.value,
                    "transcripts": scrubbed_transcripts,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
            await db.calls.update_one(
                {"call_id": session.call_id},
                call_update_payload,
                upsert=True
            )

            if lead_schema and lead_schema.intent_summary:
                lead_data = lead_schema.model_dump()
                lead_status = LeadStatus.QUALIFIED if lead_schema.qualification_score >= 70 else LeadStatus.WARM
                
                lead_update_payload = {
                    "$set": {
                        **lead_data,
                        "call_id": session.call_id,
                        "status": lead_status.value,
                        "updated_at": datetime.now(timezone.utc)
                    },
                    "$setOnInsert": {
                        "lead_id": f"lead_{session.call_id}",
                        "created_at": datetime.now(timezone.utc)
                    }
                }

                await db.leads.update_one(
                    {"call_id": session.call_id},
                    lead_update_payload,
                    upsert=True
                )
                session.lead_id = f"lead_{session.call_id}"

                await self.send_json(
                    session.websocket,
                    WSMessage(
                        event=WSMessageType.LEAD_QUALIFIED,
                        data={**lead_data, "status": lead_status.value}
                    )
                )
                logger.info(f"MongoDB lead profile upserted for Call ID: {session.call_id}")

        except Exception as e:
            logger.error(f"Error in background post-turn CRM processing: {e}", exc_info=True)

    async def _finalize_call_log(self, session: VoiceSessionState) -> None:
        """
        Calculates total session duration and marks call log as COMPLETED in MongoDB.
        """
        try:
            duration = int((datetime.now(timezone.utc) - session.start_time).total_seconds())
            db = get_db()
            await db.calls.update_one(
                {"call_id": session.call_id},
                {
                    "$set": {
                        "status": CallStatus.COMPLETED.value,
                        "duration_seconds": duration,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            logger.info(f"Call log finalized: [Call ID: {session.call_id} | Duration: {duration}s]")
        except Exception as e:
            logger.error(f"Failed to finalize call log in database: {e}")


ws_manager = WebSocketConnectionManager()