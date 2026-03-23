from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.db.models import AuditLog, User
from app.dependencies import require_owner

router = APIRouter()


@router.get("")
async def get_logs(
    page: int = 1,
    page_size: int = 50,
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    query = select(AuditLog).order_by(desc(AuditLog.created_at))
    if action:
        query = query.where(AuditLog.action.startswith(action))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    query = query.offset((page - 1) * page_size).limit(min(page_size, 200))
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "logs": [
            {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "meta": log.meta,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }