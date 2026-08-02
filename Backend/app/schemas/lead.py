from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LeadStatus(str, Enum):
    NEW = "new"
    WARM = "warm"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"


class BudgetTier(str, Enum):
    UNKNOWN = "unknown"
    UNDER_10K = "under_10k"
    TIER_10K_25K = "10k_25k"
    TIER_25K_50K = "25k_50k"
    OVER_50K = "over_50k"


class LeadExtractionToolSchema(BaseModel):
    """
    OWASP LLM02-hardened tool schema for autonomous BANT CRM qualification.
    Using extra='forbid' ensures Llama-3.3-70B cannot inject arbitrary NoSQL keys.
    """
    model_config = ConfigDict(extra="forbid")

    caller_name: Optional[str] = Field(
        default=None, 
        description="Full name of the prospect if mentioned"
    )
    company_name: Optional[str] = Field(
        default=None, 
        description="Company or organization name of the prospect"
    )
    email: Optional[str] = Field(
        default=None, 
        description="Business email address if provided"
    )
    phone: Optional[str] = Field(
        default=None, 
        description="Contact phone number if provided"
    )
    intent_summary: str = Field(
        ..., 
        description="Concise summary of customer pain points, intent, and product interest"
    )
    budget_tier: BudgetTier = Field(
        default=BudgetTier.UNKNOWN, 
        description="Estimated budget classification"
    )
    timeline: Optional[str] = Field(
        default=None, 
        description="Expected timeline for purchase or implementation (e.g., '1 month')"
    )
    authority_confirmed: bool = Field(
        default=False, 
        description="True if caller is a decision-maker or authorized buyer"
    )
    objections_raised: List[str] = Field(
        default_factory=list,
        description="List of objections raised by the prospect (e.g., 'Price too high', 'Using competitor')"
    )
    qualification_score: int = Field(
        default=50, 
        ge=0, 
        le=100, 
        description="Overall BANT qualification score from 0 to 100"
    )