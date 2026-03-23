import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.models import Memory

logger = logging.getLogger(__name__)

SYSTEM_KEYS = {"deploy_preferences", "notification_rules", "alert_thresholds"}


async def read_memory(db: AsyncSession, user_id: str, key: str) -> Any | None:
    result = await db.execute(
        select(Memory).where(Memory.user_id == user_id, Memory.key == key)
    )
    row = result.scalar_one_or_none()
    return row.value if row else None


async def write_memory(
    db: AsyncSession,
    user_id: str,
    key: str,
    value: Any,
    category: str = "preference",
) -> Memory:
    result = await db.execute(
        select(Memory).where(Memory.user_id == user_id, Memory.key == key)
    )
    row = result.scalar_one_or_none()

    if row:
        row.value = value
        row.category = category
    else:
        row = Memory(user_id=user_id, key=key, value=value, category=category)
        db.add(row)

    await db.flush()
    logger.info(f"Memory written: user={user_id} key={key}")
    return row


async def delete_memory(db: AsyncSession, user_id: str, key: str) -> bool:
    result = await db.execute(
        delete(Memory)
        .where(Memory.user_id == user_id, Memory.key == key)
        .returning(Memory.id)
    )
    return result.scalar_one_or_none() is not None


async def list_memory(db: AsyncSession, user_id: str) -> list[dict]:
    result = await db.execute(
        select(Memory).where(Memory.user_id == user_id).order_by(Memory.key)
    )
    rows = result.scalars().all()
    return [{"key": r.key, "value": r.value, "category": r.category} for r in rows]


def is_system_key(key: str) -> bool:
    return key in SYSTEM_KEYS