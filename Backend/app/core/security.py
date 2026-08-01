import re
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("vocalsync.security")

class SecurityViolationError(Exception):
    """Base exception for all security policy violations."""
    pass


class PromptInjectionDetectedError(SecurityViolationError):
    """Raised when user input matches OWASP LLM01 jailbreak/override patterns."""
    pass


class PayloadTooLargeError(SecurityViolationError):
    """Raised when user transcript exceeds maximum character length limits."""
    pass


PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous\s+rules", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a\s+)?jailbroken", re.IGNORECASE),
    re.compile(r"repeat\s+your\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"reveal\s+your\s+(system\s+)?instructions", re.IGNORECASE),
    re.compile(r"print\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"bypass\s+(security|safety|rules)", re.IGNORECASE),
    re.compile(r"dan\s+mode|do\s+anything\s+now", re.IGNORECASE),
]

PII_EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PII_PHONE_REGEX = re.compile(
    r"\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?){1,2}\d{4}\b"
)
PII_CREDIT_CARD_REGEX = re.compile(
    r"\b(?:\d[ -]*?){13,16}\b"
)


def sanitize_user_prompt(text: str) -> str:
    """
    Enforces OWASP LLM01 protection on incoming STT user transcripts.
    Checks payload size and scans for instruction-override attack patterns.
    """
    if not text:
        return ""

    text_cleaned = text.strip()

    if len(text_cleaned) > settings.MAX_PROMPT_LENGTH:
        logger.warning(
            f"Payload length violation: {len(text_cleaned)} > {settings.MAX_PROMPT_LENGTH}"
        )
        raise PayloadTooLargeError("Audio transcript exceeded maximum allowable prompt length.")

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text_cleaned):
            logger.error(
                f"OWASP LLM01 Alert: Prompt injection intercepted -> Pattern: '{pattern.pattern}'"
            )
            raise PromptInjectionDetectedError(
                "Prompt injection or system prompt override attempt detected."
            )

    return text_cleaned


def scrub_pii(text: str) -> str:
    """
    Enforces OWASP LLM06 privacy protection.
    Redacts sensitive customer contact information before persisting to MongoDB Atlas.
    """
    if not text or not settings.ENABLE_PII_SCRUBBING:
        return text

    scrubbed_text = PII_EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
    scrubbed_text = PII_PHONE_REGEX.sub("[PHONE_REDACTED]", scrubbed_text)
    scrubbed_text = PII_CREDIT_CARD_REGEX.sub("[CREDIT_CARD_REDACTED]", scrubbed_text)

    return scrubbed_text