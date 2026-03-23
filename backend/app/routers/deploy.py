import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import DeployEvent, User
from app.dependencies import require_owner
from app.tools.deploy import TriggerDeploymentTool, RollbackDeploymentTool, ListDeploymentsTool

router = APIRouter()
logger = logging.getLogger(__name__)

_trigger_tool = TriggerDeploymentTool()
_rollback_tool = RollbackDeploymentTool()
_list_tool = ListDeploymentsTool()


class TriggerRequest(BaseModel):
    branch: str = "main"
    reason: str | None = None
    confirm: bool = False


class RollbackRequest(BaseModel):
    target_deploy_id: str
    reason: str | None = None
    confirm: bool = False


@router.get("")
async def list_deployments(
    limit: int = 10,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await _list_tool.run(
        inputs={"limit": limit, **({"status": status} if status else {})},
        db=db,
        user_id=str(current_user.id),
    )
    return result.data


@router.post("/trigger")
async def trigger_deployment(
    body: TriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await _trigger_tool.run(
        inputs=body.model_dump(),
        db=db,
        user_id=str(current_user.id),
        confirmed=body.confirm,
    )
    if result.requires_confirmation:
        return {"requires_confirmation": True, "message": result.confirmation_message}
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@router.post("/rollback")
async def rollback_deployment(
    body: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await _rollback_tool.run(
        inputs=body.model_dump(),
        db=db,
        user_id=str(current_user.id),
        confirmed=body.confirm,
    )
    if result.requires_confirmation:
        return {"requires_confirmation": True, "message": result.confirmation_message}
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@router.get("/{deploy_id}/logs")
async def stream_deploy_logs(
    deploy_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    """SSE endpoint — streams deploy logs as they accumulate."""
    result = await db.execute(select(DeployEvent).where(DeployEvent.id == deploy_id))
    deploy = result.scalar_one_or_none()
    if not deploy:
        raise HTTPException(status_code=404, detail="Deploy not found")

    async def log_generator():
        # Poll DB for log updates every 2s for up to 5 minutes
        for _ in range(150):
            await asyncio.sleep(2)
            await db.refresh(deploy)
            if deploy.logs:
                yield f"data: {deploy.logs}\n\n"
            if deploy.status in ("success", "failed"):
                yield f"data: [DONE] status={deploy.status}\n\n"
                break

    return StreamingResponse(log_generator(), media_type="text/event-stream")