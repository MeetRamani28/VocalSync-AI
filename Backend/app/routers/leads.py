from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from app.db.client import get_db

router = APIRouter()


@router.get("/leads", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def list_qualified_leads(limit: int = Query(default=20, le=100)):
    """
    Retrieves BANT CRM qualified leads sorted by qualification score.
    """
    db = get_db()
    cursor = db.leads.find().sort("qualification_score", -1).limit(limit)
    leads = []
    async for doc in cursor:
        doc.pop("_id", None)
        leads.append(doc)
    return leads


@router.get("/leads/{lead_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_lead_profile(lead_id: str):
    """
    Retrieves a specific BANT lead profile by its Lead ID.
    """
    db = get_db()
    doc = await db.leads.find_one({"lead_id": lead_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Lead profile not found.")
    doc.pop("_id", None)
    return doc