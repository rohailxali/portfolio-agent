import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.memory.short_term import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Public health check endpoint.
    Returns service status for DB and Redis connectivity.
    """
    checks: dict = {"status": "ok", "db": "ok", "redis": "ok"}

    # DB check
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        checks["db"] = "error"
        checks["status"] = "degraded"

    # Redis check
    try:
        r = get_redis()
        await r.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = "error"
        checks["status"] = "degraded"

    return checks
