from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class BusinessProfileCreate(BaseModel):
    """
    Payload required from the frontend form to configure a new Business Knowledge Base.
    """
    company_name: str = Field(..., min_length=2, max_length=100, example="Surya Solar Solutions")
    product_description: str = Field(
        ..., 
        min_length=10, 
        max_length=1000, 
        example="We install residential and commercial rooftop solar power systems."
    )
    pricing_details: str = Field(
        ..., 
        min_length=5, 
        max_length=500, 
        example="3kW system is ₹1,50,000. 40% government subsidy available."
    )
    faqs: List[str] = Field(
        default_factory=list,
        example=["Installation takes 2 days.", "10-year warranty included."]
    )
    call_objective: str = Field(
        default="Schedule a free on-site consultation appointment.",
        example="Qualify customer budget and book a site visit."
    )


class BusinessProfileSchema(BusinessProfileCreate):
    """
    Complete MongoDB schema representing a stored Business Knowledge Base.
    """
    business_id: str = Field(..., description="Unique identifier for the business KB")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))