import logging
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.tools.base import BaseTool, ToolResult
from app.db.models import Lead
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


CLASSIFICATION_PROMPT = """You are a lead qualification assistant for a software developer's portfolio.

Classify the following contact form submission:

Name: {name}
Email: {email}
Message: {message}

Respond with ONLY a JSON object in this exact format:
{{
  "classification": "hot|warm|cold|spam",
  "reasoning": "one sentence explanation"
}}

Classification criteria:
- hot: Clear project request, budget mention, timeline, or immediate need
- warm: Genuine interest but vague, exploring options, or asking general questions
- cold: Just browsing, no clear intent, or irrelevant inquiry
- spam: Promotional, automated, suspicious, or clearly not a real inquiry
"""


class ClassifyLeadTool(BaseTool):
    name = "classify_lead"
    description = (
        "Use AI to classify a contact form lead as hot, warm, cold, or spam "
        "based on their message content. Updates the lead record."
    )
    requires_confirmation = False

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of the lead to classify.",
                }
            },
            "required": ["lead_id"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        try:
            lead_id = UUID(inputs["lead_id"])
        except ValueError:
            return ToolResult(success=False, error="Invalid lead_id UUID format.")

        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            return ToolResult(success=False, error=f"Lead {lead_id} not found.")

        prompt = CLASSIFICATION_PROMPT.format(
            name=lead.name,
            email=lead.email,
            message=lead.message or "(no message)",
        )

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",  # Fast + cheap for classification
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            import json
            parsed = json.loads(raw)
            classification = parsed["classification"]
            reasoning = parsed["reasoning"]

            if classification not in ("hot", "warm", "cold", "spam"):
                raise ValueError(f"Unexpected classification: {classification}")

        except Exception as e:
            logger.error(f"Lead classification failed for {lead_id}: {e}")
            return ToolResult(success=False, error=f"Classification failed: {e}")

        lead.classification = classification
        lead.status = "classified"
        await db.flush()

        logger.info(f"Lead classified: id={lead_id} classification={classification}")

        return ToolResult(
            success=True,
            data={
                "lead_id": str(lead_id),
                "classification": classification,
                "reasoning": reasoning,
                "name": lead.name,
                "email": lead.email,
            },
        )