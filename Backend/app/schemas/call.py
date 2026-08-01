from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Literal, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class Sentiment(str, Enum):
    """Real-time sentiment classification for each conversation turn."""
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    HESITANT = "Hesitant"
    NEGATIVE = "Negative"


class CallStatus(str, Enum):
    """Overall status of the voice session."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptMessage(BaseModel):
    """
    Represents a single conversational turn in the voice agent dialogue.
    """
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system"] = Field(..., description="Speaker role")
    content: str = Field(..., description="Text transcript of the spoken turn")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL, description="Sentiment badge for UI rendering")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallLogCreate(BaseModel):
    """Payload schema used when initializing or saving a call log."""
    call_id: str = Field(..., description="Unique UUID string for the session")
    caller_ip: Optional[str] = None
    status: CallStatus = CallStatus.IN_PROGRESS
    transcripts: List[TranscriptMessage] = Field(default_factory=list)
    overall_sentiment_score: float = Field(default=0.5, ge=0.0, le=1.0)
    duration_seconds: int = Field(default=0, ge=0)
    lead_id: Optional[str] = None


class CallLogInDB(CallLogCreate):
    """Full database representation of a call log stored in MongoDB."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WSMessageType(str, Enum):
    """Allowed event types for bidirectional WebSocket communication."""
    AUDIO_CHUNK = "audio_chunk"
    TEXT_TOKEN = "text_token"
    AGENT_STATE = "agent_state"
    TRANSCRIPT_UPDATE = "transcript_update"
    LEAD_QUALIFIED = "lead_qualified"
    ERROR = "error"


class WSMessage(BaseModel):
    """
    Strict payload envelope for all WebSocket messages sent between
    FastAPI and the React frontend.
    """
    model_config = ConfigDict(extra="forbid")

    event: WSMessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))