import time
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolCall, AuditLog
logger = logging.getLogger(__name__)


class ToolInput(BaseModel):
    """Base class for all tool inputs."""
    pass


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    requires_confirmation: bool = False
    confirmation_message: str | None = None


class BaseTool(ABC):
    name: str
    description: str
    requires_confirmation: bool = False

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """JSON Schema for the tool's inputs."""
        return {}

    @abstractmethod
    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        pass

    async def run(
        self,
        inputs: dict,
        db: AsyncSession,
        user_id: str,
        conversation_id: str | None = None,
        confirmed: bool = False,
    ) -> ToolResult:
        if self.requires_confirmation and not confirmed:
            return ToolResult(**{
                "success": False,
                "requires_confirmation": True,
                "confirmation_message": (
                    f"Tool `{self.name}` requires explicit confirmation. "
                    f"Re-send with confirm=true to proceed."
                ),
            })

        start = time.monotonic()
        tool_call = ToolCall(
            conversation_id=conversation_id,
            tool_name=self.name,
            inputs=inputs,
            status="pending",
            confirmed=confirmed,
        )
        db.add(tool_call)
        await db.flush()

        try:
            result = await self._execute(inputs, db, user_id)
            tool_call.status = "success" if result.success else "error"
            tool_call.outputs = result.model_dump()
        except Exception as e:
            logger.exception(f"Tool {self.name} failed: {e}")
            tool_call.status = "error"
            tool_call.outputs = {"error": str(e)}
            result = ToolResult(**{"success": False, "error": str(e)})
        finally:
            tool_call.duration_ms = int((time.monotonic() - start) * 1000)
            await db.flush()

        # Audit log
        log = AuditLog(
            user_id=user_id if user_id != "00000000-0000-0000-0000-000000000000" else None,
            action=f"tool:{self.name}",
            resource_type="tool_call",
            resource_id=str(tool_call.id),
            meta={"inputs": inputs, "status": tool_call.status},
        )
        db.add(log)
        await db.flush()

        return result