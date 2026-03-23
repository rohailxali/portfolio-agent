from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ToolResult
from app.memory.long_term import read_memory, write_memory, is_system_key


class ReadMemoryTool(BaseTool):
    name = "read_memory"
    description = "Read a stored preference or context value from long-term memory."
    requires_confirmation = False

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key to retrieve."}
            },
            "required": ["key"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        value = await read_memory(db, user_id, inputs["key"])
        if value is None:
            return ToolResult(success=True, data={"key": inputs["key"], "value": None, "found": False})
        return ToolResult(success=True, data={"key": inputs["key"], "value": value, "found": True})


class WriteMemoryTool(BaseTool):
    name = "write_memory"
    description = (
        "Store or update a preference or context value in long-term memory. "
        "System-level keys require confirmation."
    )
    requires_confirmation = False  # Confirmation handled dynamically below

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"description": "Any JSON-serializable value."},
                "category": {
                    "type": "string",
                    "enum": ["preference", "context", "fact"],
                    "default": "preference",
                },
                "confirm": {"type": "boolean", "default": False},
            },
            "required": ["key", "value"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        key = inputs["key"]
        if is_system_key(key) and not inputs.get("confirm", False):
            return ToolResult(
                success=False,
                requires_confirmation=True,
                confirmation_message=f"Key `{key}` is a system-level setting. Send with confirm=true.",
            )

        row = await write_memory(
            db,
            user_id=user_id,
            key=key,
            value=inputs["value"],
            category=inputs.get("category", "preference"),
        )
        return ToolResult(success=True, data={"key": row.key, "category": row.category})