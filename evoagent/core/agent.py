"""Top-level Agent class — assembles all modules into a runnable agent."""

from pathlib import Path
from typing import Any

from evoagent.core.result import AgentResult
from evoagent.logging.trace import TraceRecorder
from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.models.schema import LLMRequest
from evoagent.planning.critic import Critic
from evoagent.planning.executor import Executor
from evoagent.planning.loop import AgentLoop
from evoagent.planning.planner import Planner
from evoagent.planning.reflector import Reflector
from evoagent.sandbox.policy import PermissionPolicy
from evoagent.tools.builtin import create_builtin_registry
from evoagent.tools.registry import ToolRegistry


class Agent:
    """EvoAgent — a complete agent that can run tasks and chat.

    Usage:
        agent = Agent(model_router=router, tool_registry=registry)
        result = await agent.run("List the files in the current directory")
    """

    def __init__(
        self,
        model_router: ModelRouter | None = None,
        tool_registry: ToolRegistry | None = None,
        trace_recorder: TraceRecorder | None = None,
        workspace: str | Path = ".",
        permission_policy: PermissionPolicy | None = None,
        config: Any = None,
        memory_store: Any = None,
    ):
        self.workspace = Path(workspace)
        self.tool_registry = tool_registry or create_builtin_registry(self.workspace)
        self.trace_recorder = trace_recorder

        # Model router: use the provided one or a mock
        self.model_router = model_router or ModelRouter(
            providers={"default": MockLLMProvider(fixed_text="OK")}
        )

        # Planning components
        planner_llm = self._get_provider("planner")
        self.planner = Planner(planner_llm, event_logger=trace_recorder)

        executor_llm = self._get_provider("executor")
        self.executor = Executor(self.tool_registry, llm=executor_llm, event_logger=trace_recorder)

        critic_llm = self._get_provider("critic")
        self.critic = Critic(llm=critic_llm, mode="rule", event_logger=trace_recorder)

        reflector_llm = self._get_provider("planner")
        self.reflector = Reflector(llm=reflector_llm, event_logger=trace_recorder)

        self._loop = AgentLoop(
            tool_registry=self.tool_registry,
            planner=self.planner,
            executor=self.executor,
            critic=self.critic,
            reflector=self.reflector,
            trace_recorder=trace_recorder,
        )

        self.permission_policy = permission_policy
        self.memory_store = memory_store
        self._config = config
        self._memory_context: str = ""

    def _get_provider(self, role: str):
        """Get a provider for a role, falling back to default."""
        try:
            return self.model_router._get_provider(role)
        except Exception:
            return self.model_router._get_provider("default") if self.model_router._providers else None

    # ── Core API ──────────────────────────────────────────────────────

    async def run(self, task: str) -> AgentResult:
        """Run a task with memory retrieval and writing.

        Args:
            task: Natural language task description.

        Returns:
            AgentResult with success, final_answer, state, and trace.
        """
        # Pre-run: retrieve relevant memories
        self._memory_context = ""
        if self.memory_store:
            try:
                from evoagent.memory.retriever import MemoryRetriever
                retriever = MemoryRetriever(self.memory_store)
                memories = retriever.retrieve(task)
                self._memory_context = retriever.format_for_prompt(memories)
            except Exception:
                pass

        result = await self._loop.run(task, context=self._memory_context)

        # Post-run: write memory
        if self.memory_store and result.state:
            try:
                from evoagent.memory.writer import MemoryWriter
                writer = MemoryWriter(self.memory_store)
                writer.write_from_run(result.state, result.success)
            except Exception:
                pass

        return result

    async def chat(self, message: str) -> str:
        """Simple chat without tool calling.

        Args:
            message: User message.

        Returns:
            Agent response text.
        """
        provider = self._get_provider("default")
        if not provider:
            return "No model provider configured."
        response = await provider.chat(LLMRequest(
            messages=[{"role": "user", "content": message}]
        ))
        return response.content

    def add_tool(self, tool: Any) -> None:
        """Register a tool."""
        self.tool_registry.register(tool)

    def save_trace(self, path: str | Path) -> None:
        """Save trace to a directory (reserved for future use)."""
        pass
