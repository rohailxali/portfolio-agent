import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


async def send_email(subject: str, body: str, to_email: str | None = None) -> None:
    if not settings.sendgrid_api_key:
        logger.warning("SendGrid API key not configured — skipping email")
        return

    recipient = to_email or settings.notification_email_to
    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": settings.notification_email_from},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    headers = {
        "Authorization": f"Bearer {settings.sendgrid_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(SENDGRID_API_URL, json=payload, headers=headers)
        resp.raise_for_status()

    logger.info(f"Email sent to {recipient}: {subject}")