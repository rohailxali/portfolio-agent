import logging
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.tools.base import BaseTool, ToolResult
from app.db.models import DeployEvent, RollbackEvent

logger = logging.getLogger(__name__)


class TriggerDeploymentTool(BaseTool):
    name = "trigger_deployment"
    description = (
        "Dispatch a GitHub Actions workflow to redeploy the portfolio site. "
        "REQUIRES explicit confirmation. Logs the deploy event."
    )
    requires_confirmation = True

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "default": "main",
                    "description": "Git branch to deploy from.",
                },
                "reason": {
                    "type": "string",
                    "description": "Human-readable reason for this deployment.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to proceed.",
                },
            },
            "required": ["confirm"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        from app.config import get_settings
        settings = get_settings()

        branch = inputs.get("branch", settings.github_default_branch)
        reason = inputs.get("reason", "Manual trigger via agent")

        # Sanitize branch name
        if not branch.replace("-", "").replace("_", "").replace("/", "").isalnum():
            return ToolResult(success=False, error=f"Invalid branch name: {branch}")

        deploy = DeployEvent(
            trigger="manual",
            triggered_by=user_id,
            provider="github_actions",
            status="pending",
        )
        db.add(deploy)
        await db.flush()

        # Dispatch GitHub Actions workflow
        url = (
            f"https://api.github.com/repos/{settings.github_repo}"
            f"/actions/workflows/{settings.github_workflow_id}/dispatches"
        )
        headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {"ref": branch, "inputs": {"reason": reason, "deploy_id": str(deploy.id)}}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            deploy.status = "running"
        except httpx.HTTPStatusError as e:
            deploy.status = "failed"
            deploy.logs = f"GitHub API error: {e.response.text}"
            await db.flush()
            return ToolResult(success=False, error=f"GitHub dispatch failed: {e.response.status_code}")
        except Exception as e:
            deploy.status = "failed"
            await db.flush()
            return ToolResult(success=False, error=str(e))

        await db.flush()
        logger.info(f"Deployment triggered: deploy_id={deploy.id} branch={branch}")

        return ToolResult(
            success=True,
            data={
                "deploy_id": str(deploy.id),
                "status": deploy.status,
                "branch": branch,
                "workflow_url": (
                    f"https://github.com/{settings.github_repo}/actions"
                ),
            },
        )


class RollbackDeploymentTool(BaseTool):
    name = "rollback_deployment"
    description = (
        "Revert the portfolio site to a previous successful deployment. "
        "REQUIRES explicit confirmation and a valid target deploy ID."
    )
    requires_confirmation = True

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target_deploy_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "ID of the deployment to roll back to.",
                },
                "reason": {"type": "string"},
                "confirm": {"type": "boolean"},
            },
            "required": ["target_deploy_id", "confirm"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        from app.config import get_settings
        settings = get_settings()

        try:
            target_id = UUID(inputs["target_deploy_id"])
        except ValueError:
            return ToolResult(success=False, error="Invalid target_deploy_id UUID")

        result = await db.execute(
            select(DeployEvent).where(
                DeployEvent.id == target_id,
                DeployEvent.status == "success",
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            return ToolResult(
                success=False,
                error="Target deploy not found or was not successful",
            )

        rollback = RollbackEvent(
            deploy_event_id=target_id,
            triggered_by=user_id,
            confirmed=True,
            reason=inputs.get("reason", "Manual rollback via agent"),
            status="pending",
        )
        db.add(rollback)
        await db.flush()

        # Re-dispatch workflow with specific commit SHA
        if target.commit_sha:
            url = (
                f"https://api.github.com/repos/{settings.github_repo}"
                f"/actions/workflows/{settings.github_workflow_id}/dispatches"
            )
            headers = {
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            payload = {
                "ref": target.commit_sha,
                "inputs": {"rollback_id": str(rollback.id)},
            }
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                rollback.status = "running"
            except httpx.HTTPStatusError as e:
                rollback.status = "failed"
                await db.flush()
                return ToolResult(success=False, error=f"Rollback dispatch failed: {e.response.status_code}")
        else:
            rollback.status = "running"

        await db.flush()
        logger.warning(
            f"Rollback initiated: rollback_id={rollback.id} target_deploy={target_id}"
        )

        return ToolResult(
            success=True,
            data={
                "rollback_id": str(rollback.id),
                "status": rollback.status,
                "rolling_back_to": str(target_id),
                "commit_sha": target.commit_sha,
            },
        )


class ListDeploymentsTool(BaseTool):
    name = "list_deployments"
    description = "List recent deployment events with their status and metadata."
    requires_confirmation = False

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "maximum": 50},
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "success", "failed"],
                    "description": "Filter by status. Omit to return all.",
                },
            },
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        limit = min(inputs.get("limit", 10), 50)
        status_filter = inputs.get("status")

        query = select(DeployEvent).order_by(desc(DeployEvent.started_at)).limit(limit)
        if status_filter:
            query = query.where(DeployEvent.status == status_filter)

        result = await db.execute(query)
        deploys = result.scalars().all()

        return ToolResult(
            success=True,
            data={
                "deployments": [
                    {
                        "id": str(d.id),
                        "status": d.status,
                        "trigger": d.trigger,
                        "commit_sha": d.commit_sha,
                        "deploy_url": d.deploy_url,
                        "started_at": d.started_at.isoformat() if d.started_at else None,
                        "completed_at": d.completed_at.isoformat() if d.completed_at else None,
                    }
                    for d in deploys
                ]
            },
        )