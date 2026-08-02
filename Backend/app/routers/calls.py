from typing import List
from fastapi import APIRouter, HTTPException, Query, status
from app.db.client import get_db
from app.schemas.call import CallLogSchema

router = APIRouter()


@router.get("/calls", response_model=List[CallLogSchema], status_code=status.HTTP_200_OK)
async def list_call_logs(limit: int = Query(default=20, le=100)):
    """
    Retrieves recent call logs sorted by latest call timestamp.
    """
    db = get_db()
    cursor = db.calls.find().sort("created_at", -1).limit(limit)
    calls = []
    async for doc in cursor:
        doc.pop("_id", None)
        calls.append(CallLogSchema(**doc))
    return calls


@router.get("/calls/{call_id}", response_model=CallLogSchema, status_code=status.HTTP_200_OK)
async def get_call_log(call_id: str):
    """
    Retrieves a specific call log by its Call ID.
    """
    db = get_db()
    doc = await db.calls.find_one({"call_id": call_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Call log not found.")
    doc.pop("_id", None)
    return CallLogSchema(**doc)