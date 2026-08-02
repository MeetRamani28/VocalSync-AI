import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.client import MongoDBClient
from app.services.stt import stt_service
from app.websocket.manager import ws_manager
from app.websocket.twilio_manager import twilio_ws_manager
from app.routers import health, calls, leads, business, telephony

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vocalsync.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server startup and shutdown hooks.
    """
    logger.info("Starting VocalSync-AI Enterprise backend services...")
    await MongoDBClient.connect()
    yield
    logger.info("Shutting down backend services...")
    await stt_service.close()
    await MongoDBClient.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Enterprise Outbound AI Sales & Telephony Calling Platform",
    lifespan=lifespan
)

# CORS Middleware for Browser Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST Routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["System Health"])
app.include_router(calls.router, prefix=settings.API_V1_PREFIX, tags=["Call Logs"])
app.include_router(leads.router, prefix=settings.API_V1_PREFIX, tags=["CRM Leads"])
app.include_router(business.router, prefix=settings.API_V1_PREFIX, tags=["Business KB"])
app.include_router(telephony.router, prefix=settings.API_V1_PREFIX, tags=["Twilio Telephony"])


# =====================================================================
# WEBSOCKET 1: BROWSER MICROPHONE AUDIO STREAM (/ws/call/{call_id})
# =====================================================================
@app.websocket("/ws/call/{call_id}")
async def browser_voice_websocket(
    websocket: WebSocket, 
    call_id: str,
    business_id: str = Query(default="default_business")
):
    """
    Handles live browser microphone audio sessions with Dynamic KB injection.
    """
    session = await ws_manager.connect(websocket, call_id=call_id, business_id=business_id)
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            await ws_manager.handle_audio_stream(call_id=call_id, audio_bytes=audio_bytes)
    except WebSocketDisconnect:
        await ws_manager.disconnect(call_id=call_id)
    except Exception as e:
        logger.error(f"Browser WebSocket error in call {call_id}: {e}")
        await ws_manager.disconnect(call_id=call_id)


# =====================================================================
# WEBSOCKET 2: TWILIO PSTN TELEPHONY MEDIA STREAMS (/ws/twilio/{call_id})
# =====================================================================
@app.websocket("/ws/twilio/{call_id}")
async def twilio_pstn_websocket(
    websocket: WebSocket, 
    call_id: str,
    business_id: str = Query(default="default_business"),
    caller_name: str = Query(default="Prospect")
):
    """
    Handles bidirectional Twilio PSTN phone calls (mulaw 8kHz audio transcoding).
    """
    session = await twilio_ws_manager.connect(
        websocket, 
        call_id=call_id, 
        business_id=business_id,
        caller_name=caller_name
    )
    try:
        while True:
            message_text = await websocket.receive_text()
            await twilio_ws_manager.handle_twilio_message(call_id=call_id, message_str=message_text)
    except WebSocketDisconnect:
        await twilio_ws_manager.disconnect(call_id=call_id)
    except Exception as e:
        logger.error(f"Twilio PSTN WebSocket error in call {call_id}: {e}")
        await twilio_ws_manager.disconnect(call_id=call_id)