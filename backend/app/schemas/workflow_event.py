from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class EventMetrics(BaseModel):
    duration_ms: int | None = None
    tokens: int | None = None


class WorkflowEvent(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    event_type: str
    source: str = "orchestrator"
    run_id: str
    thread_id: str
    seq: int
    step_id: int | None = None
    node_id: str | None = None
    node_name: str | None = None
    node_type: str | None = None
    status: str | None = None
    visible_input: str | None = None
    visible_output: str | None = None
    tool_name: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    metrics: EventMetrics | None = None
    error: EventError | None = None
    started_at: str = Field(default_factory=iso_now)
    ended_at: str | None = None

