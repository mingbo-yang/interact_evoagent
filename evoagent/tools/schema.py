"""Tool schema — ToolCall, ToolResult, and tool-related types."""

from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.time import utc_now_iso


class ToolResult(BaseModel):
    """Standardized result from any tool execution."""

    call_id: str = Field(..., description="ID of the ToolCall this result corresponds to.")
    name: str = Field(..., description="Tool name.")
    success: bool = Field(..., description="Whether the tool executed successfully.")
    output: str = Field(default="", description="Tool output text.")
    error: str | None = Field(default=None, description="Error message if success is False.")
    artifacts: list[str] = Field(
        default_factory=list,
        description="Paths to any files or artifacts produced.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata (exit code, file size, etc.).",
    )
    started_at: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 timestamp when execution started.",
    )
    finished_at: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 timestamp when execution finished.",
    )
    duration_ms: int = Field(default=0, description="Execution duration in milliseconds.")
