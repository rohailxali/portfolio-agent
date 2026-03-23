import ssl
import socket
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.tools.base import BaseTool, ToolResult
from app.db.models import HealthCheck
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _get_ssl_expiry_days(hostname: str) -> int | None:
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(5)
            s.connect((hostname, 443))
            cert = s.getpeercert()
            expiry_str = cert["notAfter"]
            expiry = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=timezone.utc
            )
            return (expiry - datetime.now(timezone.utc)).days
    except Exception as e:
        logger.warning(f"SSL check failed for {hostname}: {e}")
        return None


class CheckWebsiteHealthTool(BaseTool):
    name = "check_website_health"
    description = (
        "Poll the portfolio website and return uptime status, HTTP status code, "
        "response time in milliseconds, and SSL certificate expiry in days."
    )
    requires_confirmation = False

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to check. Defaults to configured portfolio URL.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 10,
                    "description": "Request timeout in seconds.",
                },
            },
            "required": [],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        from app.config import get_settings
        settings = get_settings()

        url = inputs.get("url") or settings.portfolio_url
        timeout = inputs.get("timeout_seconds", 10)

        status_code = None
        response_time_ms = None
        is_up = False
        error_message = None
        ssl_expiry_days = None

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                import time
                start = time.monotonic()
                response = await client.get(url)
                response_time_ms = int((time.monotonic() - start) * 1000)
                status_code = response.status_code
                is_up = 200 <= status_code < 400
        except httpx.TimeoutException:
            error_message = "Request timed out"
        except httpx.RequestError as e:
            error_message = f"Request error: {e}"

        # SSL check (run in thread to avoid blocking)
        if url.startswith("https://"):
            hostname = url.split("//")[1].split("/")[0]
            ssl_expiry_days = await asyncio.get_event_loop().run_in_executor(
                None, _get_ssl_expiry_days, hostname
            )

        # Persist result
        hc = HealthCheck(
            url=url,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ssl_expiry_days=ssl_expiry_days,
            is_up=is_up,
            error_message=error_message,
        )
        db.add(hc)
        await db.flush()

        data = {
            "is_up": is_up,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "ssl_expiry_days": ssl_expiry_days,
            "url": url,
            "error": error_message,
        }

        if not is_up:
            logger.warning(f"Site DOWN: {url} — {error_message or status_code}")

        return ToolResult(success=True, data=data)