"""Core abstractions and runtime.

Re-exports the most commonly used types from core.types for convenience.
"""

from typing import Any as _Any

from evoagent.core.types import (  # noqa: F401
    ActionType,
    AgentContext,
    AgentResult,
    Checkpoint,
    ConfigError,
    ContentBlock,
    ContentBlockType,
    EvaluationError,
    Event,
    EventType,
    EvoAgentError,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    MemoryError,
    MemoryItem,
    MemoryType,
    Message,
    MessageRole,
    ModelProviderError,
    PermissionDeniedError,
    Plan,
    PlanningError,
    PlanStep,
    RiskLevel,
    RunStatus,
    RuntimeState,
    SandboxError,
    StepResult,
    ToolCall,
    ToolError,
    ToolResult,
    generate_id,
    safe_json_dumps,
    truncate_text,
    utc_now_iso,
)


def __getattr__(name: str) -> _Any:
    """Lazily expose eval re-exports to avoid an import cycle.

    evoagent.eval imports from evoagent.core, so importing EvalResult/EvalTask
    eagerly here would create a circular import when evoagent.eval is imported
    before evoagent.core.
    """
    if name in ("EvalResult", "EvalTask"):
        from evoagent.eval.task import EvalResult, EvalTask

        return {"EvalResult": EvalResult, "EvalTask": EvalTask}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
