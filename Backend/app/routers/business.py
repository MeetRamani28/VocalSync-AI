import uuid
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from app.db.client import get_db
from app.schemas.business import BusinessProfileCreate, BusinessProfileSchema

router = APIRouter()


@router.post("/business", response_model=BusinessProfileSchema, status_code=status.HTTP_201_CREATED)
async def create_or_update_business_kb(payload: BusinessProfileCreate):
    """
    Registers or updates a company's Dynamic Business Knowledge Base for AI injection.
    """
    db = get_db()
    business_id = "default_business"
    now = datetime.now(timezone.utc)

    kb_dict = payload.model_dump()
    update_payload = {
        "$set": {
            **kb_dict,
            "business_id": business_id,
            "updated_at": now
        },
        "$setOnInsert": {
            "created_at": now
        }
    }

    await db.businesses.update_one({"business_id": business_id}, update_payload, upsert=True)
    doc = await db.businesses.find_one({"business_id": business_id})
    doc.pop("_id", None)
    return BusinessProfileSchema(**doc)


@router.get("/business/{business_id}", response_model=BusinessProfileSchema, status_code=status.HTTP_200_OK)
async def get_business_kb(business_id: str = "default_business"):
    """
    Retrieves a specific Business Knowledge Base profile.
    """
    db = get_db()
    doc = await db.businesses.find_one({"business_id": business_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Business Knowledge Base not found.")
    doc.pop("_id", None)
    return BusinessProfileSchema(**doc)