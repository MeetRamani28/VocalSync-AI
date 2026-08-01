import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.db.client import mongo_client
from app.api.endpoints import router as api_router
from app.websocket.manager import ws_manager

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vocalsync.main")

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifecycle context manager.
    Connects to MongoDB Atlas and builds database indexes on startup,
    and cleanly closes connections on shutdown.
    """
    logger.info("Starting VocalSync-AI backend services...")
    await mongo_client.connect_to_database()
    yield
    logger.info("Shutting down VocalSync-AI backend services...")
    await mongo_client.close_database_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise AI Calling & Lead Qualification Voice Agent API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,      
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.websocket("/ws/call/{call_id}")
async def voice_websocket_endpoint(websocket: WebSocket, call_id: str):
    """
    Real-Time Voice Streaming WebSocket Endpoint.
    Handles bidirectional WebM/PCM audio byte streams and structured text events.
    
    URL: ws://yourdomain.com/ws/call/{call_id}
    """
    session = await ws_manager.connect(websocket, call_id)
    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                await ws_manager.handle_audio_stream(call_id, message["bytes"])
            elif "text" in message and message["text"]:
                logger.debug(f"Received text payload on WebSocket: {message['text']}")
                
    except WebSocketDisconnect:
        logger.info(f"Client initiated disconnect for Call ID: {call_id}")
        await ws_manager.disconnect(call_id)
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket session {call_id}: {e}", exc_info=True)
        await ws_manager.disconnect(call_id)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled system exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system support."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )