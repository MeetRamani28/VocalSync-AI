import io
import logging
from typing import Optional
from groq import AsyncGroq, APIError, APIConnectionError, BadRequestError

from app.core.config import settings
from app.core.security import sanitize_user_prompt, SecurityViolationError

logger = logging.getLogger("vocalsync.stt")

# Set of single-word or phrase noise artifacts emitted by Whisper on quiet audio
WHISPER_HALLUCINATIONS = {
    "",
    "over",
    "over.",
    "you",
    "you.",
    "yeah",
    "yeah.",
    "bye",
    "bye.",
    "thank you",
    "thank you.",
    "thanks",
    "thanks.",
    "thanks for watching",
    "thanks for watching.",
    "[blank_audio]",
    "[silence]",
    "[music]",
    "[coughing]",
    "subtitles by",
    ".",
}


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
        Transcribes audio bytes into text, filtering out Whisper hallucinations
        and enforcing OWASP LLM01 prompt injection checks.
        """
        # Reject buffers smaller than 2000 bytes (likely silence or incomplete headers)
        if not audio_bytes or len(audio_bytes) < 2000:
            return ""

        extension_map = {
            "audio/webm": "webm",
            "audio/webm;codecs=opus": "webm",
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg"
        }
        ext = extension_map.get(mime_type.lower(), "webm")
        virtual_filename = f"stream_chunk.{ext}"
        audio_file_like = (virtual_filename, io.BytesIO(audio_bytes), "audio/webm")

        try:
            transcription = await self.client.audio.transcriptions.create(
                file=audio_file_like,
                model=self.model_id,
                response_format="text",
                language="en",
                temperature=0.0
            )

            raw_text = str(transcription).strip()
            cleaned_lower = raw_text.lower().strip()
            
            # Filter out known silence artifacts and single-letter hallucinations
            if cleaned_lower in WHISPER_HALLUCINATIONS or len(cleaned_lower) <= 2:
                logger.debug(f"Filtered out STT artifact: '{raw_text}'")
                return ""

            logger.info(f"STT Complete: '{raw_text[:50]}...'")
            return sanitize_user_prompt(raw_text)

        except BadRequestError as bad_req:
            logger.warning(f"Groq rejected audio chunk as malformed: {bad_req.message}")
            return ""
        except SecurityViolationError as sec_err:
            logger.error(f"Security violation in STT transcript: {sec_err}")
            raise sec_err
        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            return ""

    async def close(self) -> None:
        await self.client.close()
        logger.info("Groq STT Async client connection closed.")


stt_service = SpeechToTextService()