import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple
from groq import AsyncGroq, APIError

from app.core.config import settings
from app.schemas.lead import LeadExtractionToolSchema, BudgetTier
from app.schemas.call import Sentiment
from app.schemas.business import BusinessProfileSchema

logger = logging.getLogger("vocalsync.llm")

# BASE DYNAMIC SYSTEM PROMPT TEMPLATE
DYNAMIC_SYSTEM_PROMPT_TEMPLATE = """You are "Alex", an elite AI Sales & Lead Qualification Representative for VocalSync-AI.
You are currently making an outbound phone call on behalf of: {company_name}.

=== YOUR BUSINESS KNOWLEDGE BASE ===
- What we sell: {product_description}
- Pricing & Offers: {pricing_details}
- Frequently Asked Questions:
{formatted_faqs}

=== SALES CONVERSATION & BANT QUALIFICATION FRAMEWORK ===
Your goal is to qualify the prospect across BANT criteria:
1. BUDGET: Do they have the budget for our pricing?
2. AUTHORITY: Are they a decision-maker?
3. NEED: What is their core business pain point?
4. TIMELINE: How soon do they want to implement a solution?

=== CONVERSATIONAL BEHAVIOR & VOICE CONSTRAINTS ===
1. CONCISE RESPONSES: Speak in 1 to 3 short, natural sentences per turn. Never output bullet points or markdown.
2. NATURAL FLOW: Match human conversational cadence. Handle objections politely and guide the call toward: "{call_objective}".
3. TOOL-CALLING GUARDRAILS:
   - Do NOT execute the extract_lead_profile tool if the user provided no substantive information or said generic words like "hello", "over", or filler.
   - NEVER write "customer is unresponsive" as the intent_summary.
"""

LEAD_EXTRACTION_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "extract_lead_profile",
        "description": "Extracts BANT lead qualification metrics, contact details, budget tier, and objections from the call history once substantive information is provided.",
        "parameters": LeadExtractionToolSchema.model_json_schema()
    }
}


class LLMEngineService:
    """
    Asynchronous LLM engine powered by Groq Llama-3.3-70B-Versatile.
    Provides sub-second token streaming, dynamic KB context injection, and BANT tool calling.
    """
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL_ID
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    def build_system_prompt(self, business_kb: Optional[BusinessProfileSchema] = None) -> str:
        """
        Dynamically builds the system prompt using the target Business Knowledge Base.
        Falls back to default VocalSync-AI sales context if no KB is provided.
        """
        if not business_kb:
            return DYNAMIC_SYSTEM_PROMPT_TEMPLATE.format(
                company_name="VocalSync-AI Enterprise",
                product_description="AI Voice Sales Agents that automate outbound calling and lead qualification.",
                pricing_details="Plans start at $299/month for 1,000 automated calling minutes.",
                formatted_faqs="  - Q: Does it integrate with CRMs? A: Yes, via Webhooks and REST API.\n  - Q: Is it real-time? A: Yes, sub-second latency.",
                call_objective="Schedule a 15-minute live product demo with our sales team."
            )

        formatted_faqs = "\n".join([f"  - {faq}" for faq in business_kb.faqs]) if business_kb.faqs else "  - None provided."
        return DYNAMIC_SYSTEM_PROMPT_TEMPLATE.format(
            company_name=business_kb.company_name,
            product_description=business_kb.product_description,
            pricing_details=business_kb.pricing_details,
            formatted_faqs=formatted_faqs,
            call_objective=business_kb.call_objective
        )

    async def generate_voice_stream(
        self, 
        conversation_history: List[Dict[str, str]],
        business_kb: Optional[BusinessProfileSchema] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams AI response tokens in real time for immediate TTS playback.
        """
        system_prompt = self.build_system_prompt(business_kb)
        messages = [{"role": "system", "content": system_prompt}] + conversation_history

        try:
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
            yield "I experienced a brief connection hiccup. Could you repeat that?"
        except Exception as e:
            logger.critical(f"Unexpected error in LLM streaming: {e}", exc_info=True)
            yield "I'm having trouble processing that right now."

    async def analyze_sentiment_and_extract_lead(
        self, 
        conversation_history: List[Dict[str, str]],
        business_kb: Optional[BusinessProfileSchema] = None
    ) -> Tuple[Sentiment, Optional[LeadExtractionToolSchema]]:
        """
        Post-turn background task: Evaluates sentiment and extracts BANT CRM lead metrics.
        """
        user_turns = [m for m in conversation_history if m["role"] == "user"]
        if not user_turns:
            return Sentiment.NEUTRAL, None

        latest_user_text = user_turns[-1]["content"].lower().strip()
        # Guardrail: Do not run tool calling for short single-word turns
        if len(latest_user_text.split()) < 2:
            return Sentiment.NEUTRAL, None

        system_prompt = self.build_system_prompt(business_kb)
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {
                "role": "user", 
                "content": "Classify user sentiment (Positive, Neutral, Hesitant, Negative). If user provided substantive BANT lead info, execute extract_lead_profile."
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
                        
                        # Guardrail: Reject "unresponsive" hallucinations
                        intent = raw_args.get("intent_summary", "").lower()
                        if "unresponsive" in intent or not intent:
                            continue

                        extracted_lead = LeadExtractionToolSchema(**raw_args)
                        logger.info(
                            f"Lead Tool Extracted: {extracted_lead.caller_name or 'Anonymous'} "
                            f"(Score: {extracted_lead.qualification_score}/100)"
                        )
                        break

            return detected_sentiment, extracted_lead

        except Exception as e:
            logger.error(f"Failed to execute lead extraction tool call: {e}")
            return Sentiment.NEUTRAL, None


llm_service = LLMEngineService()