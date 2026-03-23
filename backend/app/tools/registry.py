from app.tools.base import BaseTool
from app.tools.monitor import CheckWebsiteHealthTool
from app.tools.deploy import TriggerDeploymentTool, RollbackDeploymentTool, ListDeploymentsTool
from app.tools.content import UpdateContentTool
from app.tools.leads import ClassifyLeadTool
from app.tools.notifications import SendNotificationTool
from app.tools.memory_tools import ReadMemoryTool, WriteMemoryTool
from app.tools.logs_tool import GetLogsTool

_TOOLS: list[BaseTool] = [
    CheckWebsiteHealthTool(),
    TriggerDeploymentTool(),
    RollbackDeploymentTool(),
    ListDeploymentsTool(),
    UpdateContentTool(),
    ClassifyLeadTool(),
    SendNotificationTool(),
    ReadMemoryTool(),
    WriteMemoryTool(),
    GetLogsTool(),
]

TOOL_REGISTRY: dict[str, BaseTool] = {t.name: t for t in _TOOLS}


def get_tool(name: str) -> BaseTool | None:
    return TOOL_REGISTRY.get(name)


def get_claude_tool_definitions() -> list[dict]:
    """Format tools for Anthropic API tool_use parameter."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in _TOOLS
    ]