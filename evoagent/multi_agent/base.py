"""RoleAgent — base class for role-specific agents."""

from dataclasses import dataclass, field
from typing import Any

from evoagent.core.message import MessageRole
from evoagent.logging.event import EventType
from evoagent.logging.trace import TraceRecorder
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest
from evoagent.tools.registry import ToolRegistry


@dataclass
class RoleAgentConfig:
    """Configuration for a RoleAgent."""

    name: str = ""
    role: str = ""
    system_prompt: str = "You are a helpful assistant."
    model_role: str = "default"
    tools: list[str] | None = None
    memory_enabled: bool = False
    max_turns: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


class RoleAgent:
    """A single agent with a specific role.

    Uses ModelRouter for LLM calls (via the configured model_role),
    optionally has its own tool registry and memory store.
    All actions are recorded via the shared event logger.
    """

    def __init__(
        self,
        config: RoleAgentConfig,
        model_router: Any = None,
        tool_registry: ToolRegistry | None = None,
        memory_store: Any = None,
        trace_recorder: TraceRecorder | None = None,
    ):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.model_router = model_router
        self.tool_registry = tool_registry
        self.memory_store = memory_store
        self.trace_recorder = trace_recorder

    def _get_llm(self) -> BaseLLMProvider | None:
        if not self.model_router:
            return None
        try:
            return self.model_router._get_provider(self.config.model_role)
        except Exception:
            try:
                return self.model_router._get_provider("default")
            except Exception:
                return None

    async def act(self, message: str, context: str = "", run_id: str = "") -> str:
        """Perform one reasoning/action step.

        Args:
            message: Input message or task.
            context: Additional context.
            run_id: Shared run ID for event logging.

        Returns:
            Agent's response text.
        """
        llm = self._get_llm()
        if not llm:
            return f"[{self.name}] No LLM provider configured."

        system = self.config.system_prompt
        if context:
            system += f"\n\nContext: {context}"

        request = LLMRequest(messages=[
            {"role": MessageRole.SYSTEM.value, "content": system},
            {"role": MessageRole.USER.value, "content": message},
        ])

        # Record event
        if self.trace_recorder and run_id:
            self.trace_recorder.log(
                EventType.LLM_CALL_STARTED,
                payload={"agent": self.name, "role": self.role},
            )

        response = await llm.chat(request)

        if self.trace_recorder and run_id:
            self.trace_recorder.log(
                EventType.LLM_CALL_FINISHED,
                payload={"agent": self.name, "content": response.content[:200]},
            )

        return response.content
