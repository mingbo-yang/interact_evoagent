"""Planning schema — Plan, PlanStep, and action types."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id


class ActionType(StrEnum):
    LLM = "llm"
    TOOL = "tool"
    CODE = "code"
    ASK_USER = "ask_user"
    FINISH = "finish"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """A single step within a plan."""

    id: str = Field(
        default_factory=lambda: generate_id("step"),
        description="Unique step ID.",
    )
    goal: str = Field(..., description="What this step aims to accomplish.")
    action_type: ActionType = Field(
        default=ActionType.TOOL,
        description="Type of action: llm, tool, code, ask_user, or finish.",
    )
    tool_name: str | None = Field(
        default=None,
        description="Tool name, if action_type is 'tool'.",
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the tool or action.",
    )
    expected_result: str | None = Field(
        default=None,
        description="Expected outcome description, for validation.",
    )
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        description="Current step status.",
    )
    result: Any | None = Field(
        default=None,
        description="Step result (ToolResult or other) after execution.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata.",
    )


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Plan(BaseModel):
    """A plan composed of ordered steps to accomplish a task."""

    id: str = Field(
        default_factory=lambda: generate_id("plan"),
        description="Unique plan ID.",
    )
    task: str = Field(..., description="The original task description.")
    steps: list[PlanStep] = Field(
        default_factory=list,
        description="Ordered list of plan steps.",
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Estimated risk level of the plan.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata.",
    )
