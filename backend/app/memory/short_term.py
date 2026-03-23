import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()
    logger.info("Redis connected")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis


async def get_session_context(conversation_id: str) -> list[dict]:
    """Retrieve conversation message history from Redis."""
    r = get_redis()
    raw = await r.get(f"ctx:{conversation_id}")
    if not raw:
        return []
    return json.loads(raw)


async def set_session_context(conversation_id: str, messages: list[dict]) -> None:
    """Persist conversation message history to Redis with TTL."""
    r = get_redis()
    await r.set(
        f"ctx:{conversation_id}",
        json.dumps(messages),
        ex=settings.session_ttl_seconds,
    )


async def append_to_context(conversation_id: str, message: dict) -> list[dict]:
    """Append a single message and return updated context."""
    messages = await get_session_context(conversation_id)
    messages.append(message)
    await set_session_context(conversation_id, messages)
    return messages


async def clear_session_context(conversation_id: str) -> None:
    r = get_redis()
    await r.delete(f"ctx:{conversation_id}")


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = get_redis()
    await r.set(f"cache:{key}", json.dumps(value), ex=ttl)


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    raw = await r.get(f"cache:{key}")
    return json.loads(raw) if raw else None