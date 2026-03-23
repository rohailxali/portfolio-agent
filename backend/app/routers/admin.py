import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.dependencies import require_owner
from app.auth.service import hash_password
from app.scheduler.tasks import scheduler

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "readonly"


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "role": u.role} for u in users]


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if body.role not in ("owner", "readonly"):
        raise HTTPException(status_code=400, detail="Role must be 'owner' or 'readonly'")

    user = User(
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()
    return {"id": str(user.id), "email": user.email, "role": user.role}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    if not confirm:
        return {"requires_confirmation": True, "message": "Add ?confirm=true to delete this user."}

    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()
    logger.warning(f"User deleted: id={user_id} by={current_user.id}")
    return {"deleted": True, "user_id": user_id}


@router.get("/scheduler/tasks")
async def list_tasks(_: User = Depends(require_owner)):
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]


@router.post("/scheduler/run/{task_id}")
async def run_task_now(
    task_id: str,
    _: User = Depends(require_owner),
):
    job = scheduler.get_job(task_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` not found")
    job.modify(next_run_time=None)  # Trigger immediately
    scheduler.wakeup()
    return {"triggered": task_id}