from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, desc

from app.db.session import get_db
from app.memory.short_term import get_redis
from app.db.models import HealthCheck

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        await get_redis().ping()
        redis_ok = True
    except Exception:
        pass

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok}


@router.get("/monitor/status")
async def monitor_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HealthCheck).order_by(desc(HealthCheck.checked_at)).limit(1)
    )
    hc = result.scalar_one_or_none()
    if not hc:
        return {"message": "No health checks recorded yet"}
    return {
        "is_up": hc.is_up,
        "status_code": hc.status_code,
        "response_time_ms": hc.response_time_ms,
        "ssl_expiry_days": hc.ssl_expiry_days,
        "url": hc.url,
        "checked_at": hc.checked_at.isoformat(),
        "error": hc.error_message,
    }


@router.get("/monitor/history")
async def monitor_history(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HealthCheck).order_by(desc(HealthCheck.checked_at)).limit(min(limit, 500))
    )
    checks = result.scalars().all()
    return [
        {
            "is_up": hc.is_up,
            "status_code": hc.status_code,
            "response_time_ms": hc.response_time_ms,
            "checked_at": hc.checked_at.isoformat(),
        }
        for hc in checks
    ]