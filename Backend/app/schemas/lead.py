from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


class LeadStatus(str, Enum):
    """Lifecycle stages for an AI-qualified sales lead."""
    UNQUALIFIED = "unqualified"
    WARM = "warm"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"


class BudgetTier(str, Enum):
    """Estimated budget tiers extracted during the sales conversation."""
    UNDER_5K = "under_5k"
    TIER_5K_10K = "5k_10k"
    TIER_10K_25K = "10k_25k"
    ENTERPRISE = "enterprise"
    UNKNOWN = "unknown"


class LeadExtractionToolSchema(BaseModel):
    """
    OWASP LLM02 Hardened Tool-Calling Schema.
    This schema is passed directly to Groq Llama-3.3-70B as a LangChain/OpenAI function call.
    Every field emitted by the LLM is strictly type-checked and clamped.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    caller_name: Optional[str] = Field(
        default=None, 
        description="Full name of the caller if provided during the conversation.",
        max_length=100
    )
    email: Optional[EmailStr] = Field(
        default=None, 
        description="Valid email address of the caller."
    )
    phone: Optional[str] = Field(
        default=None, 
        description="Phone number provided by the caller.",
        max_length=25
    )
    company_name: Optional[str] = Field(
        default=None, 
        description="Company or organization name.",
        max_length=150
    )
    intent_summary: str = Field(
        ..., 
        description="1-2 sentence concise summary of the caller's primary problem or product interest.",
        max_length=500
    )
    budget_tier: BudgetTier = Field(
        default=BudgetTier.UNKNOWN, 
        description="Estimated budget tier based on conversation context."
    )
    qualification_score: int = Field(
        default=0, 
        ge=0, 
        le=100, 
        description="AI-calculated lead qualification score from 0 to 100 based on budget, urgency, and fit."
    )
    objections_raised: List[str] = Field(
        default_factory=list, 
        description="List of specific sales objections raised (e.g., 'pricing too high', 'needs custom SLA')."
    )

    @field_validator("objections_raised", mode="before")
    @classmethod
    def clamp_objections(cls, value: List[str]) -> List[str]:
        """Prevents LLM token flooding by limiting objection lists to 10 items max."""
        if isinstance(value, list):
            return [str(item)[:100] for item in value[:10]]
        return []


class LeadInDB(BaseModel):
    """
    MongoDB persistence schema for qualified CRM leads.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    lead_id: str = Field(..., description="Unique UUID for the lead")
    caller_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    intent_summary: str
    budget_tier: BudgetTier = BudgetTier.UNKNOWN
    qualification_score: int = 0
    status: LeadStatus = LeadStatus.UNQUALIFIED
    objections_raised: List[str] = Field(default_factory=list)
    call_id: str = Field(..., description="Reference to the originating Call log ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))