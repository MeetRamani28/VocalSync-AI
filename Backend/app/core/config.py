import json
from typing import List, Union, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Production-grade application configuration using Pydantic v2.
    Enforces strict type casting and fail-fast startup validation.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = Field(
        default="development", 
        description="dev, staging, or production"
    )
    PROJECT_NAME: str = Field(
        default="VocalSync-AI-Enterprise", 
        description="API Service Name"
    )
    API_V1_PREFIX: str = Field(default="/api/v1")
    DEBUG: bool = Field(default=True)

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: Union[bool, str, int]) -> bool:
        """
        Safely converts common string representations into a boolean.
        Prevents Uvicorn startup crashes from malformed .env boolean lines.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            val_lower = value.strip().lower()
            if val_lower in ("true", "1", "yes", "on", "debug", "dev", "development"):
                return True
            return False
        return False

    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed frontend origins for CORS"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """
        Safely parses CORS origins from either comma-separated strings,
        JSON array strings, or native Python lists.
        """
        if isinstance(value, str):
            value_trimmed = value.strip()
            if value_trimmed.startswith("[") and value_trimmed.endswith("]"):
                try:
                    return json.loads(value_trimmed)
                except Exception:
                    pass
            return [
                origin.strip() 
                for origin in value_trimmed.split(",") 
                if origin.strip()
            ]
        elif isinstance(value, list):
            return value
        return []

    RATE_LIMIT_DEFAULT: str = Field(default="60/minute")
    MAX_PROMPT_LENGTH: int = Field(
        default=1500, 
        description="Max allowed characters in a user voice transcript"
    )

    GROQ_API_KEY: str = Field(..., description="API key required for STT and LLM services")
    STT_MODEL_ID: str = Field(default="whisper-large-v3-turbo")
    LLM_MODEL_ID: str = Field(default="llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=1024, ge=1, le=8192)

    TTS_VOICE: str = Field(default="en-US-ChristopherNeural")
    TTS_RATE: str = Field(default="-10%")
    TTS_VOLUME: str = Field(default="+0%")

    MONGODB_URI: str = Field(..., description="MongoDB Atlas or local connection string")
    MONGODB_DB_NAME: str = Field(default="vocalsync_ai_prod")

    TWILIO_ACCOUNT_SID: Optional[str] = Field(default=None, description="Twilio Account SID")
    TWILIO_AUTH_TOKEN: Optional[str] = Field(default=None, description="Twilio Auth Token")
    TWILIO_PHONE_NUMBER: Optional[str] = Field(
        default=None, 
        description="Verified E.164 phone number for outbound calls (+91XXXXXXXXXX or +1XXXXXXXXXX)"
    )
    TWILIO_WEBHOOK_URL: str = Field(
        default="http://localhost:8000",
        description="Public webhook base URL for TwiML XML callbacks"
    )

    ENABLE_PII_SCRUBBING: bool = Field(
        default=True, 
        description="Scrub PII before database logging"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_telephony_enabled(self) -> bool:
        return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN and self.TWILIO_PHONE_NUMBER)


settings = Settings()