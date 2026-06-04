"""WorkflowEdge — connects nodes in the workflow graph."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from evoagent.core.state import RuntimeState

# Edge condition: (state) -> bool
EdgeCondition = Callable[[RuntimeState], bool]


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes in the workflow graph.

    Optional condition makes this a conditional edge:
    if condition(state) returns True, this edge is taken.
    """

    source: str = Field(..., description="Source node name.")
    target: str = Field(..., description="Target node name.")
    condition: Any = Field(default=None, description="Optional condition function.", exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def evaluate(self, state: RuntimeState) -> bool:
        """Evaluate the condition (if any). Returns True if no condition."""
        if self.condition is None:
            return True
        return self.condition(state)
