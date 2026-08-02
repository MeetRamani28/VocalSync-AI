import base64
import io
import logging
import wave
from typing import Tuple

# Use audioop-lts for Python 3.13+ compatibility while retaining backward compatibility
try:
    import audioop_lts as audioop # type: ignore
except ImportError:
    import audioop

logger = logging.getLogger("vocalsync.audio")


class AudioCodecTranscoder:
    """
    Real-time audio transcoding engine between Telephony PSTN formats (mulaw 8kHz)
    and AI processing formats (Linear PCM / WAV 16kHz & 24kHz).
    """

    @staticmethod
    def mulaw_8k_to_pcm_16k_wav(mulaw_bytes: bytes, state: tuple = None) -> Tuple[bytes, tuple]:
        """
        Converts Twilio 8,000Hz 8-bit mulaw bytes into a valid 16,000Hz 16-bit linear PCM WAV
        buffer required by Groq Whisper LPU.

        Returns:
            Tuple[bytes, tuple]: (WAV audio bytes with header, updated resampling state)
        """
        if not mulaw_bytes:
            return b"", state

        try:
            # 1. Decode 8-bit mulaw to 16-bit linear PCM at 8,000Hz
            linear_8k = audioop.ulaw2lin(mulaw_bytes, 2)

            # 2. Resample from 8,000Hz to 16,000Hz (2 channels -> mono = 1, sample width = 2)
            linear_16k, new_state = audioop.ratecv(
                linear_8k, 2, 1, 8000, 16000, state
            )

            # 3. Wrap linear PCM in a valid WAV container header in-memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)       # Mono
                wav_file.setsampwidth(2)       # 16-bit
                wav_file.setframerate(16000)   # 16 kHz
                wav_file.writeframes(linear_16k)

            wav_bytes = wav_buffer.getvalue()
            return wav_bytes, new_state

        except Exception as e:
            logger.error(f"Failed to transcode mulaw to PCM 16k WAV: {e}")
            return b"", state

    @staticmethod
    def pcm_24k_to_mulaw_8k_base64(pcm_24k_bytes: bytes, state: tuple = None) -> Tuple[str, tuple]:
        """
        Converts Edge-TTS 24,000Hz 16-bit linear PCM into base64-encoded 8,000Hz mulaw
        ready for transmission over Twilio Media Stream WebSockets.

        Returns:
            Tuple[str, tuple]: (Base64-encoded mulaw string, updated resampling state)
        """
        if not pcm_24k_bytes:
            return "", state

        try:
            # 1. Resample from 24,000Hz down to 8,000Hz telephony standard
            linear_8k, new_state = audioop.ratecv(
                pcm_24k_bytes, 2, 1, 24000, 8000, state
            )

            # 2. Encode 16-bit linear PCM into 8-bit mulaw
            mulaw_8k = audioop.lin2ulaw(linear_8k, 2)

            # 3. Base64 encode for Twilio WebSocket JSON payload
            base64_payload = base64.b64encode(mulaw_8k).decode("utf-8")
            return base64_payload, new_state

        except Exception as e:
            logger.error(f"Failed to transcode PCM 24k to base64 mulaw: {e}")
            return "", state

    @staticmethod
    def is_valid_wav_header(data: bytes) -> bool:
        """
        Quick diagnostic check to verify if a byte array starts with a valid RIFF/WAV header.
        """
        return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


audio_codec = AudioCodecTranscoder()