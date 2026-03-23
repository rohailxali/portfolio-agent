import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_discord_notification(subject: str, body: str) -> None:
    if not settings.discord_webhook_url:
        logger.warning("Discord webhook not configured — skipping")
        return

    content = f"**{subject}**\n{body}" if subject else body
    payload = {"content": content}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(settings.discord_webhook_url, json=payload)
        resp.raise_for_status()

    logger.info(f"Discord notification sent: {subject}")