"""Event schema for the logging subsystem."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso


class EventType(StrEnum):
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    LLM_CALL_STARTED = "llm_call_started"
    LLM_CALL_FINISHED = "llm_call_finished"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SHELL_EXEC = "shell_exec"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    CRITIC_FEEDBACK = "critic_feedback"
    CHECKPOINT_CREATED = "checkpoint_created"
    ERROR = "error"
    FINAL_RESULT = "final_result"


class Event(BaseModel):
    """A single event in the agent execution trace.

    All agent actions (LLM calls, tool executions, file operations,
    memory reads/writes, errors, results) are recorded as Events
    and written to a JSONL log.
    """

    id: str = Field(
        default_factory=lambda: generate_id("evt"),
        description="Unique event ID.",
    )
    run_id: str = Field(..., description="ID of the run this event belongs to.")
    step_id: str | None = Field(
        default=None,
        description="ID of the step this event belongs to, if any.",
    )
    timestamp: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 event timestamp.",
    )
    event_type: EventType = Field(..., description="Type of event.")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data (tool args, LLM response, etc.).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata.",
    )
