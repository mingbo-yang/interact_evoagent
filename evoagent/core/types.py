"""Core schema re-exports and utility functions.

Import everything from this module for convenient access:

    from evoagent.core.types import Message, ToolCall, ToolResult, Event, ...
"""

import json
from typing import Any

# ── Context ───────────────────────────────────────────────────────────
from evoagent.core.context import AgentContext  # noqa: F401

# ── Errors ────────────────────────────────────────────────────────────
from evoagent.core.errors import (  # noqa: F401
    ConfigError,
    EvaluationError,
    EvoAgentError,
    MemoryError,
    ModelProviderError,
    PermissionDeniedError,
    PlanningError,
    SandboxError,
    ToolError,
)

# ── IDs & time ────────────────────────────────────────────────────────
from evoagent.core.ids import generate_id  # noqa: F401

# ── Messages ──────────────────────────────────────────────────────────
from evoagent.core.message import (  # noqa: F401
    ContentBlock,
    ContentBlockType,
    Message,
    MessageRole,
    ToolCall,
)

# ── Results ───────────────────────────────────────────────────────────
from evoagent.core.result import (  # noqa: F401
    AgentResult,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)

# ── State ─────────────────────────────────────────────────────────────
from evoagent.core.state import (  # noqa: F401
    Checkpoint,
    RunStatus,
    RuntimeState,
    StepResult,
)
from evoagent.core.time import utc_now_iso  # noqa: F401
from evoagent.eval.task import EvalResult, EvalTask  # noqa: F401
from evoagent.logging.event import Event, EventType  # noqa: F401
from evoagent.memory.schema import MemoryItem, MemoryType  # noqa: F401

# ── Sub-module schemas ────────────────────────────────────────────────
from evoagent.planning.schema import (  # noqa: F401
    ActionType,
    Plan,
    PlanStep,
    RiskLevel,
    StepStatus,
)
from evoagent.tools.schema import ToolResult  # noqa: F401

# ── Utility functions ─────────────────────────────────────────────────


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """Safely serialize an object to JSON string.

    Handles non-serializable types by falling back to str().

    Args:
        obj: The object to serialize.
        **kwargs: Passed to json.dumps.

    Returns:
        JSON string.
    """
    try:
        return json.dumps(obj, default=str, ensure_ascii=False, **kwargs)
    except Exception:
        return json.dumps({"error": "json_serialization_failed", "type": type(obj).__name__})


def truncate_text(text: str, max_length: int = 8000, ellipsis: str = "\n... (truncated)") -> str:
    """Truncate text to a maximum length.

    Args:
        text: The text to truncate.
        max_length: Maximum character count.
        ellipsis: Suffix appended when truncated.

    Returns:
        Truncated text, or original if within limit.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis


# Rebuild models with forward references after all imports are resolved
RuntimeState.model_rebuild()
Checkpoint.model_rebuild()
AgentResult.model_rebuild()
