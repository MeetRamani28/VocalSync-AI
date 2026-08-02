import logging
import uuid
from fastapi import APIRouter, HTTPException, Request, Response, status
from app.services.telephony import telephony_service
from app.schemas.telephony import OutboundCallRequest, OutboundCallResponse

logger = logging.getLogger("vocalsync.telephony_router")
router = APIRouter()


@router.post("/telephony/dial", response_model=OutboundCallResponse, status_code=status.HTTP_200_OK)
async def dial_outbound_prospect(payload: OutboundCallRequest):
    """
    Triggers an outbound PSTN phone call to a prospect using Twilio REST API.
    """
    try:
        call_id = f"call_{uuid.uuid4()}"
        response = await telephony_service.initiate_outbound_call(
            to_phone_number=payload.phone_number,
            call_id=call_id,
            caller_name=payload.caller_name or "Prospect",
            business_id=payload.business_id or "default_business"
        )
        return response
    except Exception as e:
        logger.error(f"Failed to initiate outbound PSTN call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telephony/twiml", status_code=status.HTTP_200_OK)
async def generate_twilio_stream_twiml(request: Request):
    """
    Webhook endpoint called by Twilio when a prospect answers the phone.
    Returns dynamic TwiML XML to open an audio WebSocket stream.
    """
    query_params = request.query_params
    call_id = query_params.get("call_id", f"call_{uuid.uuid4()}")
    host = request.headers.get("host", "localhost:8000")

    xml_content = telephony_service.generate_twiml_stream_xml(call_id=call_id, request_host=host)
    return Response(content=xml_content, media_type="application/xml")


@router.post("/telephony/status", status_code=status.HTTP_200_OK)
async def log_twilio_call_status(request: Request):
    """
    Webhook endpoint called by Twilio to log call state changes (ringing, answered, completed).
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        logger.info(f"Twilio PSTN Status Update -> SID: {call_sid} | Status: {call_status}")
    except Exception as e:
        logger.warning(f"Error parsing Twilio status webhook: {e}")
    return {"status": "received"}