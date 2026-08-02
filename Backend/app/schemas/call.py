from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CallStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    HESITANT = "Hesitant"
    NEGATIVE = "Negative"


class WSMessageType(str, Enum):
    AGENT_STATE = "agent_state"
    TRANSCRIPT_UPDATE = "transcript_update"
    TEXT_TOKEN = "text_token"
    LEAD_QUALIFIED = "lead_qualified"
    TELEPHONY_EVENT = "telephony_event"
    ERROR = "error"


class WSMessage(BaseModel):
    event: WSMessageType
    data: Dict[str, Any]


class TranscriptMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Spoken transcript text")
    sentiment: Optional[Sentiment] = Field(default=Sentiment.NEUTRAL)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallLogSchema(BaseModel):
    call_id: str = Field(..., description="Unique UUID for call session")
    business_id: Optional[str] = Field(default=None, description="Linked business KB ID")
    phone_number: Optional[str] = Field(default=None, description="Outbound destination E.164 number")
    status: CallStatus = Field(default=CallStatus.IN_PROGRESS)
    duration_seconds: int = Field(default=0, ge=0)
    transcripts: List[TranscriptMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))