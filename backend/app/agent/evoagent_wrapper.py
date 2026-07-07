from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evoagent.core.agent import Agent
from evoagent.models.router import ModelRouter
from evoagent.tools.builtin import create_builtin_registry


@dataclass
class ToolCallRecord:
    name: str
    success: bool
    output: str
    error: str | None = None
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    answer: str
    success: bool
    tool_calls: list[ToolCallRecord]
    steps: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


class EvoAgentWrapper:
    """Wrapper around EvoAgent that surfaces its internal tool calls and wires
    per-tool approval to the interactive host.

    EvoAgent has native file-edit / patch / run_tests / git_diff / bash tools,
    so it modifies repos, produces diffs, and runs tests on its own — no
    external code agent required.

    The registry is built with ``auto_approve=True`` so the *tool layer* does not
    double-gate; the real approval decision for ASK actions is delegated to the
    ``approval_hook`` passed to :meth:`run_full`, which the orchestrator bridges
    to the in-chat approval prompt. Genuinely destructive commands are still
    blocked by the policy's DENY rules before the hook is ever consulted.
    """

    def __init__(self, workspace: str | None = None):
        ws = Path(workspace) if workspace else Path.cwd()
        tools = create_builtin_registry(ws, auto_approve=True)

        if os.getenv("DEEPSEEK_API_KEY"):
            from evoagent.models.deepseek import DeepSeekProvider

            provider: Any = DeepSeekProvider()
        else:
            from evoagent.models.factory import MockLLMProvider

            provider = MockLLMProvider(fixed_text="Task executed.")

        router = ModelRouter(
            providers={
                "planner": provider,
                "executor": provider,
                "critic": provider,
                "default": provider,
            }
        )
        self._agent = Agent(model_router=router, tool_registry=tools, workspace=ws)

    async def run_full(
        self,
        user_input: str,
        approval_hook: Any = None,
        tool_event_hook: Any = None,
    ) -> AgentRunResult:
        # Bind per-run hooks so ASK actions can be approved live in the chat and
        # tool events streamed. Read by the ReAct engine at run() time.
        self._agent.approval_hook = approval_hook
        self._agent.tool_event_hook = tool_event_hook
        try:
            result = await self._agent.run(user_input)
        finally:
            self._agent.approval_hook = None
            self._agent.tool_event_hook = None
        answer = result.final_answer or result.error or "No answer generated."

        tool_calls: list[ToolCallRecord] = []
        state = result.state
        if state is not None:
            for tr in state.tool_results:
                tool_calls.append(
                    ToolCallRecord(
                        name=tr.name,
                        success=tr.success,
                        output=tr.output or "",
                        error=tr.error,
                        duration_ms=int(getattr(tr, "duration_ms", 0) or 0),
                        metadata=dict(tr.metadata or {}),
                    )
                )
        return AgentRunResult(
            answer=answer,
            success=result.success,
            tool_calls=tool_calls,
            steps=int(getattr(result, "steps_taken", 0) or 0),
            total_tokens=int(getattr(result, "total_tokens", 0) or 0),
            total_cost=float(getattr(result, "total_cost", 0.0) or 0.0),
        )

    async def run(self, user_input: str) -> str:
        return (await self.run_full(user_input)).answer
