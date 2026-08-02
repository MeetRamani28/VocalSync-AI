from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TwilioCallStatus(str, Enum):
    QUEUED = "queued"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"


class OutboundCallRequest(BaseModel):
    """
    REST payload submitted from the frontend Outbound Dialer card.
    """
    phone_number: str = Field(
        ..., 
        description="E.164 phone number to dial (e.g., +919876543210 or +18005550199)"
    )
    caller_name: Optional[str] = Field(
        default="Valued Prospect", 
        description="Prospect's name for personalized AI greeting"
    )
    business_id: Optional[str] = Field(
        default="default_business", 
        description="Target Business Knowledge Base ID to inject into the AI prompt"
    )


class OutboundCallResponse(BaseModel):
    """
    Response returned to the frontend when Twilio accepts the outbound call trigger.
    """
    status: str = Field(..., example="initiated")
    call_id: str = Field(..., example="call_d5cf1aa0-57fd-4ff0-993a-b97bf4aca0e6")
    twilio_sid: str = Field(..., example="CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    message: str = Field(..., example="Outbound call successfully dispatched to PSTN network.")


class TwilioStreamEvent(BaseModel):
    """
    Standard JSON envelope received from Twilio Media Streams over WebSocket.
    """
    event: str = Field(..., description="'connected', 'start', 'media', or 'stop'")
    sequenceNumber: Optional[str] = None
    media: Optional[Dict[str, Any]] = None
    streamSid: Optional[str] = None
    start: Optional[Dict[str, Any]] = None