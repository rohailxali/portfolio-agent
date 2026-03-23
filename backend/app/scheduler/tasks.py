import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import AsyncSessionLocal
from app.tools.monitor import CheckWebsiteHealthTool
from app.notifications.slack import send_slack_notification
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
scheduler = AsyncIOScheduler()

_monitor_tool = CheckWebsiteHealthTool()
_last_was_up: bool = True  # Track state to avoid repeat alerts


async def run_health_check():
    global _last_was_up
    async with AsyncSessionLocal() as db:
        result = await _monitor_tool.run(
            inputs={}, db=db, user_id="00000000-0000-0000-0000-000000000000", confirmed=False
        )
        if result.success and result.data:
            is_up = result.data.get("is_up", True)

            # Only alert on state change: was up → now down
            if not is_up and _last_was_up:
                logger.error(f"DOWNTIME DETECTED: {result.data}")
                if settings.slack_webhook_url:
                    await send_slack_notification(
                        subject="🚨 Portfolio Site Down",
                        body=f"Site is unreachable.\nURL: {result.data.get('url')}\nError: {result.data.get('error')}",
                    )
            elif is_up and not _last_was_up:
                logger.info("Site recovered")
                if settings.slack_webhook_url:
                    await send_slack_notification(
                        subject="✅ Portfolio Site Recovered",
                        body=f"Site is back up. Response: {result.data.get('response_time_ms')}ms",
                    )

            _last_was_up = is_up
        await db.commit()


def start_scheduler():
    scheduler.add_job(
        run_health_check,
        trigger=IntervalTrigger(seconds=60),
        id="health_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()