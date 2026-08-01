import re
import logging
from typing import Tuple, List
from .config import settings

logger = logging.getLogger("vocalsync.security")

class SecurityViolationError(Exception):
    """Base exception for security-related policy violations."""
    pass


class PromptInjectionDetectedError(SecurityViolationError):
    """Raised when an adversarial prompt injection attempt is detected."""
    def __init__(self, pattern_matched: str, message: str = "Potential prompt injection detected."):
        self.pattern_matched = pattern_matched
        super().__init__(f"{message} (Pattern: '{pattern_matched}')")


class PayloadTooLargeError(SecurityViolationError):
    """Raised when input length exceeds safe processing limits (DDOS prevention)."""
    pass


PII_EMAIL_REGEX = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
    re.IGNORECASE
)
PII_PHONE_REGEX = re.compile(
    r'\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b'
)
PII_CREDIT_CARD_REGEX = re.compile(
    r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b'
)

PROMPT_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a\s+|an\s+)?(?:DAN|unfiltered|jailbroken)", re.IGNORECASE),
    re.compile(r"repeat\s+the\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"what\s+are\s+your\s+initial\s+instructions", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"bypass\s+(?:security|safety|filter)", re.IGNORECASE),
    re.compile(r"system:\s*", re.IGNORECASE), # Attempting to fake a system role token
]


def scrub_pii(text: str) -> str:
    """
    Masks Personally Identifiable Information (PII) from text strings.
    Used before persisting call transcripts or telemetry to MongoDB Atlas.
    
    Args:
        text (str): Raw input text or transcription.
    Returns:
        str: Text with emails, phone numbers, and credit cards replaced by tags.
    """
    if not text or not settings.ENABLE_PII_SCRUBBING:
        return text

    scrubbed_text = PII_EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
    scrubbed_text = PII_PHONE_REGEX.sub("[PHONE_REDACTED]", scrubbed_text)
    scrubbed_text = PII_CREDIT_CARD_REGEX.sub("[CARD_REDACTED]", scrubbed_text)
    
    return scrubbed_text


def sanitize_user_prompt(prompt_text: str) -> str:
    """
    Validates and cleanses incoming user speech transcripts before they are
    sent to the Groq LLM engine.
    
    Enforces:
    1. Strict length limits to prevent Token Flooding / DoS.
    2. Zero-tolerance pattern matching for prompt injection keywords.
    3. Basic whitespace normalization.
    
    Args:
        prompt_text (str): Transcribed speech from Whisper STT.
    Returns:
        str: Cleaned and validated string ready for LLM consumption.
    Raises:
        PayloadTooLargeError: If input exceeds configured character limit.
        PromptInjectionDetectedError: If malicious injection keywords are found.
    """
    if not prompt_text:
        return ""

    cleaned_text = prompt_text.strip()

    if len(cleaned_text) > settings.MAX_PROMPT_LENGTH:
        logger.warning(
            f"Security Alert: Payload exceeded limit ({len(cleaned_text)} > {settings.MAX_PROMPT_LENGTH})"
        )
        raise PayloadTooLargeError(
            f"Input audio transcript exceeds maximum allowed length of {settings.MAX_PROMPT_LENGTH} characters."
        )

    for pattern in PROMPT_INJECTION_PATTERNS:
        match = pattern.search(cleaned_text)
        if match:
            matched_text = match.group(0)
            logger.error(f"Security Alert: Prompt Injection detected! Pattern: '{matched_text}'")
            raise PromptInjectionDetectedError(pattern_matched=matched_text)

    return cleaned_text


def validate_and_prepare_log_payload(transcript: str) -> Tuple[str, bool]:
    """
    Helper utility for the database logging layer. Scopes text for logging
    and returns a tuple of (scrubbed_text, was_modified).
    """
    scrubbed = scrub_pii(transcript)
    was_modified = scrubbed != transcript
    if was_modified:
        logger.info("PII scrubbed from transcript payload prior to database write.")
    return scrubbed, was_modified