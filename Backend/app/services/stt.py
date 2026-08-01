import io
import logging
from typing import Optional
from groq import AsyncGroq, APIError, APIConnectionError

from app.core.config import settings
from app.core.security import sanitize_user_prompt, SecurityViolationError

logger = logging.getLogger("vocalsync.stt")


class SpeechToTextService:
    """
    Asynchronous Speech-to-Text (STT) engine using Groq LPU Whisper-Large-V3-Turbo.
    Handles raw audio byte streams, error recovery, and security sanitization.
    """
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model_id = settings.STT_MODEL_ID

    async def transcribe_audio_buffer(
        self, 
        audio_bytes: bytes, 
        mime_type: str = "audio/webm"
    ) -> str:
        """
        Transcribes raw audio bytes from a WebSocket stream into text and 
        applies OWASP LLM01 prompt injection sanitization.

        Args:
            audio_bytes (bytes): Binary audio data (WebM, WAV, OGG, or MP3).
            mime_type (str): Format hint for the file envelope.
        Returns:
            str: Cleaned, sanitized transcription string.
        Raises:
            RuntimeError: If Groq API fails or audio buffer is invalid.
            SecurityViolationError: If transcription contains adversarial injection.
        """
        if not audio_bytes or len(audio_bytes) == 0:
            logger.warning("Empty audio buffer received; skipping transcription.")
            return ""

        extension_map = {
            "audio/webm": "webm",
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg"
        }
        ext = extension_map.get(mime_type.lower(), "webm")
        virtual_filename = f"stream_chunk.{ext}"

        audio_file_like = (virtual_filename, io.BytesIO(audio_bytes), mime_type)

        logger.debug(f"Sending {len(audio_bytes)} bytes to Groq STT ({self.model_id})...")

        try:
            transcription = await self.client.audio.transcriptions.create(
                file=audio_file_like,
                model=self.model_id,
                response_format="text",
                language="en",
                temperature=0.0 
            )

            raw_text = str(transcription).strip()
            if not raw_text or raw_text in ["", "[BLANK_AUDIO]", "[SILENCE]"]:
                logger.debug("Whisper detected silence or blank audio.")
                return ""

            logger.info(f"STT Complete: '{raw_text[:50]}...'")

            sanitized_text = sanitize_user_prompt(raw_text)
            return sanitized_text

        except SecurityViolationError as sec_err:
            logger.error(f"Security violation in STT transcript: {sec_err}")
            raise sec_err

        except APIConnectionError as conn_err:
            logger.error(f"Groq API Connection failed: {conn_err}")
            raise RuntimeError("Speech-to-text service is temporarily unreachable.") from conn_err

        except APIError as api_err:
            logger.error(f"Groq API Error ({api_err.status_code}): {api_err.message}")
            raise RuntimeError(f"Speech transcription failed: {api_err.message}") from api_err

        except Exception as e:
            logger.critical(f"Unexpected exception in STT service: {e}", exc_info=True)
            raise RuntimeError("Internal speech-to-text processing error.") from e

    async def close(self) -> None:
        """Gracefully closes the underlying httpx async client pool."""
        await self.client.close()
        logger.info("Groq STT Async client connection closed.")


stt_service = SpeechToTextService()