import asyncio
import base64
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional, List
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import scrub_pii, PromptInjectionDetectedError, PayloadTooLargeError
from app.db.client import get_db
from app.schemas.call import CallStatus, Sentiment, TranscriptMessage
from app.schemas.lead import LeadStatus
from app.schemas.business import BusinessProfileSchema
from app.services.stt import stt_service
from app.services.llm import llm_service
from app.services.tts import tts_service
from app.utils.audio_codec import audio_codec

logger = logging.getLogger("vocalsync.twilio_ws")

SENTENCE_BOUNDARY_REGEX = re.compile(r"([.?!])\s*")


class TwilioSessionState:
    """
    In-memory state container for an active PSTN telephone call session.
    """
    def __init__(
        self, 
        call_id: str, 
        websocket: WebSocket,
        business_kb: Optional[BusinessProfileSchema] = None,
        caller_name: str = "Prospect"
    ):
        self.call_id = call_id
        self.websocket = websocket
        self.business_kb = business_kb
        self.caller_name = caller_name
        self.stream_sid: Optional[str] = None
        self.history: List[Dict[str, str]] = []
        self.status = CallStatus.IN_PROGRESS
        self.start_time = datetime.now(timezone.utc)
        self.latest_sentiment = Sentiment.NEUTRAL
        self.audio_buffer = bytearray()
        self.resample_state_in = None
        self.resample_state_out = None


class TwilioWebSocketManager:
    """
    Enterprise real-time Twilio Media Streams manager.
    Transcodes bidirectional telephony mulaw (8kHz) <-> PCM/WAV (16kHz/24kHz).
    """
    def __init__(self):
        self.active_sessions: Dict[str, TwilioSessionState] = {}

    async def connect(
        self, 
        websocket: WebSocket, 
        call_id: str, 
        business_id: Optional[str] = None,
        caller_name: str = "Prospect"
    ) -> TwilioSessionState:
        """
        Accepts Twilio TwiML WebSocket handshake and initializes PSTN session.
        """
        await websocket.accept()

        business_kb = None
        if business_id:
            try:
                db = get_db()
                kb_data = await db.businesses.find_one({"business_id": business_id})
                if kb_data:
                    business_kb = BusinessProfileSchema(**kb_data)
                    logger.info(f"Loaded Business KB '{business_kb.company_name}' for PSTN Call: {call_id}")
            except Exception as e:
                logger.warning(f"Could not load Business KB '{business_id}': {e}")

        session = TwilioSessionState(
            call_id=call_id,
            websocket=websocket,
            business_kb=business_kb,
            caller_name=caller_name
        )
        self.active_sessions[call_id] = session
        logger.info(f"Twilio PSTN WebSocket connected: [Call ID: {call_id}]")
        return session

    async def disconnect(self, call_id: str) -> None:
        """
        Cleans up PSTN session state and finalizes database call logs.
        """
        session = self.active_sessions.pop(call_id, None)
        if session:
            logger.info(f"Twilio PSTN WebSocket closed: [Call ID: {call_id}]")
            asyncio.create_task(self._finalize_call_log(session))

    async def handle_twilio_message(self, call_id: str, message_str: str) -> None:
        """
        Parses Twilio JSON envelopes: 'connected', 'start', 'media', and 'stop'.
        """
        session = self.active_sessions.get(call_id)
        if not session:
            return

        try:
            packet = json.loads(message_str)
            event_type = packet.get("event")

            if event_type == "connected":
                logger.info(f"Twilio Media Stream protocol handshake connected: [Call ID: {call_id}]")

            elif event_type == "start":
                session.stream_sid = packet.get("streamSid")
                logger.info(f"Twilio Media Stream started: [Stream SID: {session.stream_sid}]")
                # Trigger proactive AI opening greeting
                asyncio.create_task(self._send_initial_greeting(session))

            elif event_type == "media":
                media_payload = packet.get("media", {})
                base64_audio = media_payload.get("payload", "")
                if base64_audio:
                    raw_mulaw = base64.b64decode(base64_audio)
                    session.audio_buffer.extend(raw_mulaw)
                    
                    # Process audio in ~1.5 second chunks (12,000 bytes at 8,000Hz 8-bit)
                    if len(session.audio_buffer) >= 12000:
                        chunk_to_process = bytes(session.audio_buffer)
                        session.audio_buffer.clear()
                        asyncio.create_task(self._process_twilio_audio_chunk(session, chunk_to_process))

            elif event_type == "stop":
                logger.info(f"Twilio Media Stream stopped by PSTN network: [Call ID: {call_id}]")
                await self.disconnect(call_id)

        except Exception as e:
            logger.error(f"Error handling Twilio WebSocket message: {e}", exc_info=True)

    async def _send_initial_greeting(self, session: TwilioSessionState) -> None:
        """
        Speaks a personalized opening greeting when the prospect answers the phone.
        """
        company = session.business_kb.company_name if session.business_kb else "VocalSync-AI"
        greeting = f"Hello {session.caller_name}, this is Alex calling from {company}. Am I catching you at a good time?"
        session.history.append({"role": "assistant", "content": greeting})
        logger.info(f"Speaking opening greeting to PSTN call: '{greeting}'")
        await self._stream_tts_to_twilio(session, greeting)

    async def _process_twilio_audio_chunk(self, session: TwilioSessionState, mulaw_bytes: bytes) -> None:
        """
        Transcodes incoming mulaw bytes -> linear PCM/WAV -> Whisper STT -> LLM -> Edge-TTS -> mulaw.
        """
        try:
            # 1. Transcode 8kHz mulaw to 16kHz linear PCM WAV for Groq Whisper
            wav_bytes, session.resample_state_in = audio_codec.mulaw_8k_to_pcm_16k_wav(
                mulaw_bytes, 
                session.resample_state_in
            )
            
            transcript = await stt_service.transcribe_audio_buffer(wav_bytes, mime_type="audio/wav")
            if not transcript:
                return

            session.history.append({"role": "user", "content": transcript})
            logger.info(f"PSTN User Transcript: '{transcript}'")

            # 2. Generate Llama-3.3-70B response with Business KB injection
            full_assistant_response = ""
            sentence_buffer = ""

            async for token in llm_service.generate_voice_stream(session.history, business_kb=session.business_kb):
                full_assistant_response += token
                sentence_buffer += token

                if SENTENCE_BOUNDARY_REGEX.search(sentence_buffer):
                    await self._stream_tts_to_twilio(session, sentence_buffer.strip())
                    sentence_buffer = ""

            if sentence_buffer.strip():
                await self._stream_tts_to_twilio(session, sentence_buffer.strip())

            session.history.append({"role": "assistant", "content": full_assistant_response})
            logger.info(f"PSTN AI Response: '{full_assistant_response[:60]}...'")

            # 3. Trigger BANT lead qualification and PII scrubbing in background
            asyncio.create_task(self._async_post_turn_processing(session))

        except PromptInjectionDetectedError as pie:
            logger.error(f"OWASP LLM01 Prompt Injection intercepted on PSTN: {pie}")
            await self._stream_tts_to_twilio(
                session, 
                "I am a VocalSync AI assistant and can only discuss sales qualification and product details."
            )
        except Exception as e:
            logger.error(f"Error processing Twilio audio chunk: {e}", exc_info=True)

    async def _stream_tts_to_twilio(self, session: TwilioSessionState, text: str) -> None:
        """
        Synthesizes text into Edge-TTS (24kHz PCM) and transcodes to base64 mulaw (8kHz)
        for immediate transmission over Twilio Media Streams.
        """
        if not text or not session.stream_sid:
            return

        try:
            async for pcm_chunk in tts_service.stream_audio_from_text(text):
                base64_mulaw, session.resample_state_out = audio_codec.pcm_24k_to_mulaw_8k_base64(
                    pcm_chunk, 
                    session.resample_state_out
                )
                if base64_mulaw:
                    media_message = {
                        "event": "media",
                        "streamSid": session.stream_sid,
                        "media": {"payload": base64_mulaw}
                    }
                    await session.websocket.send_text(json.dumps(media_message))
        except Exception as e:
            logger.error(f"Failed to stream TTS audio to Twilio PSTN: {e}")

    async def _async_post_turn_processing(self, session: TwilioSessionState) -> None:
        """
        Background task: Evaluates sentiment, extracts BANT CRM lead data,
        scrubs PII (OWASP LLM06), and writes updates to MongoDB Atlas.
        """
        try:
            sentiment, lead_schema = await llm_service.analyze_sentiment_and_extract_lead(
                session.history, 
                business_kb=session.business_kb
            )
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
                    "business_id": session.business_kb.business_id if session.business_kb else None,
                    "status": CallStatus.IN_PROGRESS.value,
                    "transcripts": scrubbed_transcripts,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
            await db.calls.update_one({"call_id": session.call_id}, call_update_payload, upsert=True)

            if lead_schema and lead_schema.intent_summary:
                lead_data = lead_schema.model_dump()

                # Fix for MongoDB E11000 Duplicate Key Error
                if not lead_data.get("email"):
                    lead_data.pop("email", None)
                if not lead_data.get("phone"):
                    lead_data.pop("phone", None)

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
                await db.leads.update_one({"call_id": session.call_id}, lead_update_payload, upsert=True)
                session.lead_id = f"lead_{session.call_id}"
                logger.info(f"MongoDB BANT lead profile upserted for PSTN Call ID: {session.call_id}")

        except Exception as e:
            logger.error(f"Error in Twilio PSTN background CRM processing: {e}", exc_info=True)

    async def _finalize_call_log(self, session: TwilioSessionState) -> None:
        """
        Calculates total duration and marks PSTN call as COMPLETED in MongoDB.
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
            logger.info(f"Twilio PSTN call log finalized: [Call ID: {session.call_id} | Duration: {duration}s]")
        except Exception as e:
            logger.error(f"Failed to finalize PSTN call log: {e}")


twilio_ws_manager = TwilioWebSocketManager()