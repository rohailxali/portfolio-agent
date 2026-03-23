import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ToolResult
from app.db.models import Notification
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limit: tracked in Redis
RATE_LIMIT_KEY = "notif:rate"
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW = 3600  # 1 hour


class SendNotificationTool(BaseTool):
    name = "send_notification"
    description = (
        "Send a notification via email, Slack, or Discord. "
        "Rate-limited to 20 per hour across all channels."
    )
    requires_confirmation = False

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "enum": ["email", "slack", "discord"],
                    "description": "Delivery channel.",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line (used for email).",
                },
                "body": {
                    "type": "string",
                    "description": "Notification body text.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "default": "normal",
                },
            },
            "required": ["channel", "body"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        from app.memory.short_term import get_redis

        channel = inputs["channel"]
        subject = inputs.get("subject", "Portfolio Agent Notification")
        body = inputs["body"]

        # Rate limit check
        r = get_redis()
        count = await r.incr(RATE_LIMIT_KEY)
        if count == 1:
            await r.expire(RATE_LIMIT_KEY, RATE_LIMIT_WINDOW)
        if count > RATE_LIMIT_MAX:
            return ToolResult(success=False, error="Notification rate limit exceeded (20/hour).")

        # Create DB record
        notif = Notification(
            user_id=user_id,
            type=channel,
            channel=channel,
            subject=subject,
            body=body,
            status="pending",
        )
        db.add(notif)
        await db.flush()

        # Dispatch to the appropriate channel
        try:
            if channel == "email":
                from app.notifications.email import send_email
                await send_email(subject=subject, body=body)
            elif channel == "slack":
                from app.notifications.slack import send_slack_notification
                await send_slack_notification(subject=subject, body=body)
            elif channel == "discord":
                from app.notifications.discord import send_discord_notification
                await send_discord_notification(subject=subject, body=body)

            notif.status = "sent"
            from datetime import datetime, timezone
            notif.sent_at = datetime.now(timezone.utc)

        except Exception as e:
            notif.status = "failed"
            notif.meta = {"error": str(e)}
            await db.flush()
            logger.error(f"Notification failed: channel={channel} error={e}")
            return ToolResult(success=False, error=f"Notification dispatch failed: {e}")

        await db.flush()
        return ToolResult(
            success=True,
            data={"notification_id": str(notif.id), "channel": channel, "status": "sent"},
        )