"""Evaluation schema — EvalTask, EvalResult, and metrics."""

from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso


class EvalTask(BaseModel):
    """A single evaluation task / benchmark case.

    Supports multiple task types: text, tool, code, memory, rag.
    """

    task_id: str = Field(default_factory=lambda: generate_id("eval"), description="Unique task ID.")
    instruction: str = Field(..., description="Task instruction for the agent.")
    task_type: str = Field(default="text", description="Task type: text, tool, code, memory, rag.")
    workspace: str | None = Field(default=None, description="Path to workspace directory.")
    input_files: dict[str, str] = Field(default_factory=dict, description="Files to create before running: {path: content}.")
    expected_output: str | None = Field(default=None, description="Expected output text for comparison.")
    expected_check: str | None = Field(default=None, description="Checker specification as JSON string.")
    test_command: str | None = Field(default=None, description="Shell command to run as automated check.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata (difficulty, category, tags, etc.).")


class EvalResult(BaseModel):
    """Result of running an EvalTask."""

    task_id: str = Field(..., description="ID of the evaluated task.")
    run_id: str = Field(..., description="ID of the agent run.")
    success: bool = Field(..., description="Whether the task succeeded.")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized score, 0.0 to 1.0.")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Detailed metrics.")
    error: str | None = Field(default=None, description="Error message if evaluation itself failed.")
    trace_path: str | None = Field(default=None, description="Path to the event trace for this run.")
    started_at: str = Field(default_factory=utc_now_iso)
    finished_at: str = Field(default_factory=utc_now_iso)
    duration_ms: int = Field(default=0)
    cost_usd: float = Field(default=0.0, description="Total cost in USD.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata.")
