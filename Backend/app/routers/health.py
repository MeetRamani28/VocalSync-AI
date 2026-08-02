import logging
from fastapi import APIRouter, HTTPException, status
from app.db.client import get_db
from app.core.config import settings

logger = logging.getLogger("vocalsync.health")
router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def check_system_health():
    """
    Checks MongoDB connection status and Twilio telephony readiness.
    """
    db_ok = False
    try:
        db = get_db()
        await db.command("ping")
        db_ok = True
    except Exception as e:
        logger.error(f"Healthcheck database ping failed: {e}")

    return {
        "status": "online" if db_ok else "degraded",
        "database_connected": db_ok,
        "telephony_enabled": settings.is_telephony_enabled,
        "environment": settings.ENVIRONMENT,
        "service": settings.PROJECT_NAME
    }