"""WorkflowNode — a single node in the workflow graph."""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from evoagent.core.state import RuntimeState

# Node handler: async (state, context) -> state
NodeHandler = Callable[[RuntimeState, dict[str, Any]], Awaitable[RuntimeState]]


class WorkflowNode(BaseModel):
    """A node in the workflow graph.

    Each node has a handler function that takes the current
    RuntimeState and optional context, and returns an updated
    RuntimeState.
    """

    name: str = Field(..., description="Unique node name.")
    description: str = Field(default="", description="Human-readable description.")
    handler: Any = Field(default=None, description="Async handler function.", exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def execute(self, state: RuntimeState, context: dict[str, Any] | None = None) -> RuntimeState:
        """Execute the node's handler."""
        if self.handler is None:
            return state
        ctx = context or {}
        return await self.handler(state, ctx)
