import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_slack_notification(subject: str, body: str) -> None:
    if not settings.slack_webhook_url:
        logger.warning("Slack webhook not configured — skipping")
        return

    text = f"*{subject}*\n{body}" if subject else body
    payload = {"text": text}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(settings.slack_webhook_url, json=payload)
        resp.raise_for_status()

    logger.info(f"Slack notification sent: {subject}")