"""Event types for UI communication."""

from enum import StrEnum

from pydantic import BaseModel, Field


class UIEventType(StrEnum):
    SESSION_STARTED = "session_started"
    TURN_STARTED = "turn_started"
    ASSISTANT_TEXT_DELTA = "assistant_text_delta"
    ASSISTANT_TEXT_FINISHED = "assistant_text_finished"
    REASONING_SUMMARY = "reasoning_summary"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"
    TOOL_CALL_FAILED = "tool_call_failed"
    TURN_FINISHED = "turn_finished"
    TURN_FAILED = "turn_failed"
    MODE_CHANGED = "mode_changed"
    MODEL_CHANGED = "model_changed"


class UIEvent(BaseModel):
    type: UIEventType = Field(...)
    session_id: str = ""
    turn_id: str = ""
    payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
