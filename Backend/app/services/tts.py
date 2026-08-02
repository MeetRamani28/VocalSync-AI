import logging
from typing import AsyncGenerator
import edge_tts

from app.core.config import settings

logger = logging.getLogger("vocalsync.tts")


class TextToSpeechService:
    """
    Asynchronous Text-to-Speech (TTS) engine using Microsoft Edge-TTS.
    Streams audio chunks immediately to minimize speech latency.
    """
    def __init__(self):
        self.voice = settings.TTS_VOICE
        self.rate = settings.TTS_RATE
        self.volume = settings.TTS_VOLUME

    async def stream_audio_from_text(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Synthesizes text into audio chunks and streams bytes in real time.
        """
        if not text or not text.strip():
            return

        clean_text = text.strip()
        logger.debug(f"Synthesizing TTS: '{clean_text[:40]}...' [Rate: {self.rate}]")

        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume
            )

            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and chunk["data"]:
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}", exc_info=True)


tts_service = TextToSpeechService()