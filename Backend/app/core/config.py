from typing import List, Union
from pydantic import AnyHttpUrl, Field, field_validator
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

    ENVIRONMENT: str = Field(default="development", description="dev, staging, or production")
    PROJECT_NAME: str = Field(default="VocalSync-AI", description="API Service Name")
    API_V1_PREFIX: str = Field(default="/api/v1")
    DEBUG: bool = Field(default=True)

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed frontend origins for CORS"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """Parses comma-separated CORS origins from environment strings."""
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        elif isinstance(value, list):
            return value
        return []

    RATE_LIMIT_DEFAULT: str = Field(default="60/minute")
    MAX_PROMPT_LENGTH: int = Field(default=1500, description="Max allowed characters in a user voice transcript")

    GROQ_API_KEY: str = Field(..., description="API key required for STT and LLM services")
    STT_MODEL_ID: str = Field(default="whisper-large-v3-turbo")
    LLM_MODEL_ID: str = Field(default="llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=1024, ge=1, le=8192)

    TTS_VOICE: str = Field(default="en-US-ChristopherNeural")
    TTS_RATE: str = Field(default="+5%")
    TTS_VOLUME: str = Field(default="+0%")

    MONGODB_URI: str = Field(..., description="MongoDB Atlas or local connection string")
    MONGODB_DB_NAME: str = Field(default="vocalsync_ai_prod")

    ENABLE_PII_SCRUBBING: bool = Field(default=True, description="Scrub PII before database logging")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()