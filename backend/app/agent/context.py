"""
Agent context helpers.

The main conversation context (short-term memory) is managed by
app.memory.short_term (Redis). This module provides any additional
per-request context utilities needed by the orchestrator.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """
    Holds the in-flight context for a single agent turn.
    Passed around internally; not persisted between requests.
    """
    user_id: str
    conversation_id: str
    confirmed_action: dict | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
