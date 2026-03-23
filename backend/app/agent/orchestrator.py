import json
import logging

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.memory.short_term import get_session_context, set_session_context
from app.tools.registry import get_tool, get_claude_tool_definitions
from app.tools.base import ToolResult

logger = logging.getLogger(__name__)
settings = get_settings()

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are the Portfolio Agent — an AI system that manages Rohail's portfolio website.

You have tools to:
- Check website health and uptime
- Trigger and roll back deployments
- Update portfolio content
- Classify and manage leads
- Send notifications
- Read and write long-term memory
- Query audit logs

Rules:
1. Always validate that required inputs are present before calling a tool.
2. For destructive actions (deploy, rollback, delete, publish), remind the user that confirmation is required.
3. Be concise. Give the user the most relevant information, not everything.
4. If a tool call fails, explain why and suggest what to do.
5. Never expose API keys, secrets, or internal IDs unnecessarily.
6. When asked about history, use get_logs first.
"""


async def run_agent(
    user_message: str,
    conversation_id: str,
    user_id: str,
    db: AsyncSession,
    confirmed_action: dict | None = None,
) -> dict:
    """
    Run one turn of the agent loop.
    Returns: { reply: str, tool_calls: list, requires_confirmation: bool, pending_action: dict | None }
    """
    messages = await get_session_context(conversation_id)
    messages.append({"role": "user", "content": user_message})

    tool_calls_made = []
    pending_action = None
    requires_confirmation = False

    # If the user is confirming a pending action, inject that context
    if confirmed_action:
        messages.append({
            "role": "assistant",
            "content": f"[System: User confirmed action `{confirmed_action['tool_name']}` with confirm=true]",
        })

    max_iterations = 8  # Safety: prevent infinite tool loops

    for _ in range(max_iterations):
        response = await _client.messages.create(
            model=settings.agent_model,
            max_tokens=settings.agent_max_tokens,
            system=SYSTEM_PROMPT,
            tools=get_claude_tool_definitions(),
            messages=messages,
        )

        # Collect assistant message content for history
        assistant_content = response.content
        messages.append({"role": "assistant", "content": _serialize_content(assistant_content)})

        if response.stop_reason == "end_turn":
            # No more tool calls; extract text reply
            reply = _extract_text(assistant_content)
            break

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in assistant_content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_inputs = block.input
                tool_use_id = block.id

                logger.info(f"Agent calling tool: {tool_name} inputs={tool_inputs}")
                tool_calls_made.append({"tool": tool_name, "inputs": tool_inputs})

                tool = get_tool(tool_name)
                if not tool:
                    result = ToolResult(success=False, error=f"Unknown tool: {tool_name}")
                else:
                    result = await tool.run(
                        inputs=tool_inputs,
                        db=db,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        confirmed=tool_inputs.get("confirm", False),
                    )

                if result.requires_confirmation:
                    requires_confirmation = True
                    pending_action = {
                        "tool_name": tool_name,
                        "inputs": tool_inputs,
                        "confirmation_message": result.confirmation_message,
                    }

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result.model_dump()),
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        reply = _extract_text(assistant_content) or "An unexpected error occurred."
        break
    else:
        reply = "Agent reached maximum iterations. Please try a simpler request."

    await set_session_context(conversation_id, messages)

    return {
        "reply": reply,
        "tool_calls": tool_calls_made,
        "requires_confirmation": requires_confirmation,
        "pending_action": pending_action,
    }


def _extract_text(content: list) -> str:
    return " ".join(
        block.text for block in content if hasattr(block, "text") and block.text
    ).strip()


def _serialize_content(content: list) -> list[dict]:
    """Convert Anthropic SDK content blocks to plain dicts for Redis storage."""
    result = []
    for block in content:
        if hasattr(block, "text"):
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return result