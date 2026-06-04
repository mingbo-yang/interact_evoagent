"""Human interrupt — pause workflow for human approval."""

from enum import StrEnum

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso


class InterruptType(StrEnum):
    APPROVAL = "approval"
    CLARIFICATION = "clarification"
    CHOICE = "choice"


class InterruptRequest(BaseModel):
    """A request for human intervention.

    When a node sets state.status = WAITING_FOR_HUMAN,
    the runtime pauses and returns the state with an
    InterruptRequest in metadata.
    """

    id: str = Field(default_factory=lambda: generate_id("int"))
    reason: str = Field(default="", description="Why human input is needed.")
    request_type: InterruptType = Field(default=InterruptType.APPROVAL)
    requested_action: str = Field(default="", description="What action needs approval.")
    options: list[str] = Field(default_factory=list, description="Available choices.")
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


def create_approval_request(action: str, reason: str = "") -> InterruptRequest:
    """Create an approval interrupt."""
    return InterruptRequest(
        reason=reason or f"Approve action: {action}",
        request_type=InterruptType.APPROVAL,
        requested_action=action,
    )


def create_clarification_request(question: str) -> InterruptRequest:
    return InterruptRequest(
        reason=question,
        request_type=InterruptType.CLARIFICATION,
    )


def create_choice_request(question: str, options: list[str]) -> InterruptRequest:
    return InterruptRequest(
        reason=question,
        request_type=InterruptType.CHOICE,
        options=options,
    )
