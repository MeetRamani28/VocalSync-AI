import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings
from app.schemas.telephony import OutboundCallResponse

logger = logging.getLogger("vocalsync.telephony")


class TelephonyService:
    """
    Twilio PSTN Telephony service.
    Manages outbound call dispatching, Verified Caller ID validation,
    and TwiML WebSocket stream generation.
    """

    def __init__(self):
        self._client: Optional[Client] = None
        self._init_twilio_client()

    def _init_twilio_client(self) -> None:
        """
        Initializes the Twilio REST Client if credentials are present in .env.
        """
        if settings.is_telephony_enabled:
            try:
                self._client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio REST Telephony client successfully initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self._client = None
        else:
            logger.warning("Twilio credentials missing in .env; Telephony service is disabled.")

    async def initiate_outbound_call(
        self,
        to_phone_number: str,
        call_id: str,
        caller_name: str = "Prospect",
        business_id: str = "default_business"
    ) -> OutboundCallResponse:
        """
        Triggers an outbound call over PSTN using Twilio REST API.
        Connects the prospect directly to our live WebSocket media stream handler.
        """
        if not self._client or not settings.is_telephony_enabled:
            raise RuntimeError("Telephony service is not configured. Add Twilio credentials to .env.")

        # Construct dynamic TwiML Webhook URL with session context parameters
        webhook_url = (
            f"{settings.TWILIO_WEBHOOK_URL.rstrip('/')}/api/v1/telephony/twiml"
            f"?call_id={call_id}&business_id={business_id}&caller_name={caller_name}"
        )

        logger.info(f"Dispatching outbound call: [To: {to_phone_number} | Caller ID: {settings.TWILIO_PHONE_NUMBER}]")

        try:
            call = self._client.calls.create(
                to=to_phone_number,
                from_=settings.TWILIO_PHONE_NUMBER,
                url=webhook_url,
                status_callback=f"{settings.TWILIO_WEBHOOK_URL.rstrip('/')}/api/v1/telephony/status",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                timeout=30
            )

            logger.info(f"Outbound call successfully initiated -> Twilio SID: {call.sid}")

            return OutboundCallResponse(
                status="initiated",
                call_id=call_id,
                twilio_sid=call.sid,
                message="Outbound call successfully dispatched to PSTN network."
            )

        except TwilioRestException as twilio_err:
            logger.error(f"Twilio REST API Error ({twilio_err.code}): {twilio_err.msg}")
            raise RuntimeError(f"Twilio telephony error: {twilio_err.msg}") from twilio_err
        except Exception as e:
            logger.critical(f"Unexpected error triggering outbound call: {e}", exc_info=True)
            raise RuntimeError("Internal telephony dispatch failure.") from e

    @staticmethod
    def generate_twiml_stream_xml(call_id: str, request_host: str) -> str:
        """
        Generates standard TwiML XML instructing Twilio to open a bidirectional
        audio WebSocket connection to our FastAPI backend.
        """
        # Ensure wss:// protocol for secure cloud deployments, ws:// for local development
        protocol = "wss" if "localhost" not in request_host and "127.0.0.1" not in request_host else "ws"
        stream_url = f"{protocol}://{request_host}/ws/twilio/{call_id}"

        twiml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{stream_url}">
            <Parameter name="call_id" value="{call_id}" />
        </Stream>
    </Connect>
</Response>"""
        return twiml_xml.strip()


telephony_service = TelephonyService()