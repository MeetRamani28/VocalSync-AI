import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple
from groq import AsyncGroq, APIError

from app.core.config import settings
from app.schemas.lead import LeadExtractionToolSchema, BudgetTier
from app.schemas.call import Sentiment

logger = logging.getLogger("vocalsync.llm")

SYSTEM_PROMPT = """You are "Alex", an elite AI Sales & Lead Qualification Representative for VocalSync-AI.
Your goal is to have a natural, helpful, and high-converting phone conversation with potential business clients.

=== CONVERSATIONAL BEHAVIOR & VOICE CONSTRAINTS ===
1. CONCISE RESPONSES: Speak in 1 to 3 short sentences per turn. Never output bullet points, markdown tables, or wall of text.
2. NATURAL FLOW: Match human conversational cadence. Avoid sounding like a rigid robot or a customer support form.
3. PAIN POINT DISCOVERY: Ask open-ended questions about their current sales outreach, lead volume, or call latency bottlenecks.
4. OBJECTION HANDLING:
   - Price/Budget Objections: Highlight that VocalSync-AI eliminates manual caller salaries and runs on 100% free open-source infrastructure models.
   - Quality/Latency Objections: Emphasize sub-1-second streaming latency powered by LPU acceleration.
   - Integration Objections: Confirm seamless CRM sync via WebSockets and MongoDB APIs.

=== MISSION ===
Qualify the lead by discovering their:
- Contact Information (Name, Email, Phone)
- Business Needs & Intent
- Estimated Budget Tier
Once you gather these details, continue the conversation seamlessly while the background engine registers the lead.
"""

LEAD_EXTRACTION_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "extract_lead_profile",
        "description": "Extracts lead qualification metrics, contact details, budget tier, and objections from the call history.",
        "parameters": LeadExtractionToolSchema.model_json_schema()
    }
}


class LLMEngineService:
    """
    Asynchronous LLM engine powered by Groq Llama-3.3-70B-Versatile.
    Provides sub-second token streaming, sentiment analysis, and tool calling.
    """
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL_ID
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    async def generate_voice_stream(
        self, 
        conversation_history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """
        Streams conversational text tokens in real-time from Llama-3.3-70B.
        Token streams are yielded directly to the TTS engine for zero-latency audio synthesis.

        Args:
            conversation_history (List[Dict[str, str]]): Standard OpenAI role messages.
        Yields:
            str: Token chunks as they arrive from Groq LPU hardware.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

        try:
            logger.debug(f"Initiating Groq LLM token stream ({self.model})...")
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )

            async for chunk in stream:
                delta_text = chunk.choices[0].delta.content
                if delta_text:
                    yield delta_text

        except APIError as api_err:
            logger.error(f"Groq LLM Streaming API Error: {api_err}")
            yield "I apologize, but I experienced a brief connection hiccup. Could you repeat that?"
        except Exception as e:
            logger.critical(f"Unexpected error in LLM streaming: {e}", exc_info=True)
            yield "I'm having trouble processing that right now. Let's continue in a moment."

    async def analyze_sentiment_and_extract_lead(
        self, 
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[Sentiment, Optional[LeadExtractionToolSchema]]:
        """
        Executes a background tool-calling analysis on the latest conversation history.
        Extracts structured lead details (OWASP LLM02 validated) and turn sentiment.

        Args:
            conversation_history: Full transcript history of the call.
        Returns:
            Tuple[Sentiment, Optional[LeadExtractionToolSchema]]: The detected sentiment badge and validated lead model.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history,
            {
                "role": "user", 
                "content": "Analyze the latest turn. Classify user sentiment as Positive, Neutral, Hesitant, or Negative. Also execute the extract_lead_profile tool with any collected customer information."
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[LEAD_EXTRACTION_TOOL_SPEC],
                tool_choice="auto",
                temperature=0.1 
            )

            response_message = response.choices[0].message
            detected_sentiment = Sentiment.NEUTRAL

            content_lower = (response_message.content or "").lower()
            if "positive" in content_lower:
                detected_sentiment = Sentiment.POSITIVE
            elif "hesitant" in content_lower:
                detected_sentiment = Sentiment.HESITANT
            elif "negative" in content_lower:
                detected_sentiment = Sentiment.NEGATIVE

            extracted_lead: Optional[LeadExtractionToolSchema] = None
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "extract_lead_profile":
                        raw_args = json.loads(tool_call.function.arguments)
                        extracted_lead = LeadExtractionToolSchema(**raw_args)
                        logger.info(
                            f"Lead Tool Extracted Successfully: {extracted_lead.caller_name or 'Anonymous'} "
                            f"(Score: {extracted_lead.qualification_score})"
                        )
                        break

            return detected_sentiment, extracted_lead

        except Exception as e:
            logger.error(f"Failed to execute lead extraction tool call: {e}")
            return Sentiment.NEUTRAL, None


llm_service = LLMEngineService()