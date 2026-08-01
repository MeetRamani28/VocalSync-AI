import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.client import get_db, mongo_client
from app.schemas.call import CallLogInDB, CallStatus
from app.schemas.lead import LeadInDB, LeadStatus

logger = logging.getLogger("vocalsync.api")

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check() -> Dict[str, Any]:
    """
    Service health check endpoint. Verifies database reachability
    and returns system readiness status.
    """
    db_healthy = await mongo_client.ping()
    return {
        "status": "online" if db_healthy else "degraded",
        "database_connected": db_healthy,
        "service": "VocalSync-AI Core API"
    }


@router.get(
    "/calls", 
    response_model=List[CallLogInDB], 
    status_code=status.HTTP_200_OK,
    tags=["Calls"]
)
async def list_recent_calls(
    limit: int = Query(default=20, ge=1, le=100, description="Max calls to retrieve"),
    status_filter: Optional[CallStatus] = Query(default=None, description="Filter by status"),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Retrieves recent call logs sorted by creation timestamp descending.
    Transcripts returned by this endpoint are already PII-scrubbed per OWASP LLM06.
    """
    query = {}
    if status_filter:
        query["status"] = status_filter.value

    cursor = db.calls.find(query).sort("created_at", -1).limit(limit)
    calls = []
    async for document in cursor:
        calls.append(document)
    return calls


@router.get(
    "/calls/{call_id}", 
    response_model=CallLogInDB, 
    status_code=status.HTTP_200_OK,
    tags=["Calls"]
)
async def get_call_by_id(
    call_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """
    Fetches the complete transcript and metadata for a specific call ID.
    """
    document = await db.calls.find_one({"call_id": call_id})
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Call log with ID '{call_id}' not found."
        )
    return document


@router.get(
    "/leads", 
    response_model=List[LeadInDB], 
    status_code=status.HTTP_200_OK,
    tags=["Leads"]
)
async def list_qualified_leads(
    min_score: int = Query(default=0, ge=0, le=100, description="Minimum AI qualification score"),
    status_filter: Optional[LeadStatus] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Fetches AI-qualified CRM leads sorted by qualification score descending.
    """
    query: Dict[str, Any] = {"qualification_score": {"$gte": min_score}}
    if status_filter:
        query["status"] = status_filter.value

    cursor = db.leads.find(query).sort("qualification_score", -1).limit(limit)
    leads = []
    async for document in cursor:
        leads.append(document)
    return leads


@router.get("/analytics/summary", status_code=status.HTTP_200_OK, tags=["Analytics"])
async def get_analytics_summary(
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """
    Provides real-time aggregate sales performance metrics to power the frontend
    Analytics Card and Executive Dashboard.
    """
    total_calls = await db.calls.count_documents({})
    completed_calls = await db.calls.count_documents({"status": CallStatus.COMPLETED.value})
    qualified_leads = await db.leads.count_documents({"status": LeadStatus.QUALIFIED.value})
    warm_leads = await db.leads.count_documents({"status": LeadStatus.WARM.value})

    pipeline = [
        {"$match": {"status": CallStatus.COMPLETED.value}},
        {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_seconds"}}}
    ]
    agg_result = []
    async for row in db.calls.aggregate(pipeline):
        agg_result.append(row)
    
    avg_duration = round(agg_result[0]["avg_duration"], 1) if agg_result else 0.0
    conversion_rate = round((qualified_leads / total_calls * 100), 2) if total_calls > 0 else 0.0

    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "qualified_leads": qualified_leads,
        "warm_leads": warm_leads,
        "avg_call_duration_seconds": avg_duration,
        "conversion_rate_percent": conversion_rate,
    }