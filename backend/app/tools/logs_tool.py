from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.tools.base import BaseTool, ToolResult
from app.db.models import AuditLog


class GetLogsTool(BaseTool):
    name = "get_logs"
    description = "Retrieve audit logs filtered by time range, action type, or resource."
    requires_confirmation = False

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "from_time": {"type": "string", "format": "date-time"},
                "to_time": {"type": "string", "format": "date-time"},
                "action": {"type": "string", "description": "Filter by action prefix, e.g. 'tool:'."},
                "limit": {"type": "integer", "default": 50, "maximum": 500},
            },
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        limit = min(inputs.get("limit", 50), 500)
        query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)

        if from_time := inputs.get("from_time"):
            query = query.where(AuditLog.created_at >= datetime.fromisoformat(from_time))
        if to_time := inputs.get("to_time"):
            query = query.where(AuditLog.created_at <= datetime.fromisoformat(to_time))
        if action := inputs.get("action"):
            query = query.where(AuditLog.action.startswith(action))

        result = await db.execute(query)
        logs = result.scalars().all()

        return ToolResult(
            success=True,
            data={
                "logs": [
                    {
                        "id": str(log.id),
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "metadata": log.metadata,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ],
                "total": len(logs),
            },
        )