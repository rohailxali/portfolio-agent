from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.db.session import get_db
from app.db.models import User
from app.dependencies import require_owner
from app.memory.long_term import read_memory, write_memory, delete_memory, list_memory

router = APIRouter()


class MemoryWrite(BaseModel):
    value: Any
    category: str = "preference"


@router.get("")
async def list_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    return await list_memory(db, str(current_user.id))


@router.get("/{key}")
async def get_key(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    value = await read_memory(db, str(current_user.id), key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    return {"key": key, "value": value}


@router.put("/{key}")
async def upsert_key(
    key: str,
    body: MemoryWrite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    row = await write_memory(db, str(current_user.id), key, body.value, body.category)
    return {"key": row.key, "category": row.category}


@router.delete("/{key}")
async def delete_key(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    deleted = await delete_memory(db, str(current_user.id), key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    return {"deleted": True, "key": key}