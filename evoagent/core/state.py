"""RuntimeState — the single source of truth for agent execution state."""

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.message import Message
from evoagent.core.time import utc_now_iso
from evoagent.tools.schema import ToolResult

if TYPE_CHECKING:
    from evoagent.planning.schema import Plan


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepResult(BaseModel):
    """The result of executing a single plan step."""

    step_id: str = Field(..., description="ID of the executed step.")
    success: bool = Field(..., description="Whether the step succeeded.")
    output: Any | None = Field(default=None, description="Step output.")
    error: str | None = Field(default=None, description="Error message if failed.")
    started_at: str = Field(default_factory=utc_now_iso)
    finished_at: str = Field(default_factory=utc_now_iso)
    duration_ms: int = Field(default=0)


class Checkpoint(BaseModel):
    """A saved snapshot of RuntimeState for resume support."""

    id: str = Field(
        default_factory=lambda: generate_id("chk"),
        description="Unique checkpoint ID.",
    )
    state: "RuntimeState | None" = Field(
        default=None,
        description="The saved runtime state.",
    )
    timestamp: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 checkpoint timestamp.",
    )
    can_resume: bool = Field(default=True, description="Whether this checkpoint is resumable.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeState(BaseModel):
    """The complete runtime state of an agent execution.

    This is the central state object — passed between Planner,
    Executor, and Critic, saved as checkpoints, and used to
    resume interrupted runs.
    """

    run_id: str = Field(
        default_factory=lambda: generate_id("run"),
        description="Unique run ID.",
    )
    task: str = Field(default="", description="The original task description.")
    status: RunStatus = Field(
        default=RunStatus.CREATED,
        description="Current run status.",
    )
    messages: list[Message] = Field(
        default_factory=list,
        description="Full conversation history.",
    )
    plan: "Plan | None" = Field(
        default=None,
        description="Current plan, if one has been created.",
    )
    current_step_id: str | None = Field(
        default=None,
        description="ID of the currently executing step.",
    )
    step_results: list[StepResult] = Field(
        default_factory=list,
        description="Results of completed steps.",
    )
    tool_results: list[ToolResult] = Field(
        default_factory=list,
        description="Results of all tool calls in this run.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages encountered during the run.",
    )
    checkpoints: list[Checkpoint] = Field(
        default_factory=list,
        description="Saved checkpoints for this run.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata.",
    )
    created_at: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 creation timestamp.",
    )
    updated_at: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 last update timestamp.",
    )

    model_config = {"arbitrary_types_allowed": False}

    # ── Helper methods ────────────────────────────────────────────────

    def touch(self) -> None:
        """Update the updated_at timestamp to now."""
        self.updated_at = utc_now_iso()

    def add_error(self, error: str) -> None:
        """Append an error message and touch the timestamp."""
        self.errors.append(error)
        self.touch()

    def add_tool_result(self, result: "ToolResult") -> None:
        """Append a ToolResult and touch the timestamp."""
        self.tool_results.append(result)
        self.touch()

    def add_step_result(self, result: "StepResult") -> None:
        """Append a StepResult and touch the timestamp."""
        self.step_results.append(result)
        self.touch()

    def save_json(self, path: str) -> None:
        """Save RuntimeState to a JSON file."""
        from pathlib import Path
        Path(path).write_text(self.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str) -> "RuntimeState":
        """Load RuntimeState from a JSON file."""
        from pathlib import Path
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))




