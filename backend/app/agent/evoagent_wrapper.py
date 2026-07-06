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
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    answer: str
    success: bool
    tool_calls: list[ToolCallRecord]


class EvoAgentWrapper:
    """Wrapper around EvoAgent that surfaces its internal tool calls.

    EvoAgent has native file-edit / patch / run_tests / git_diff / bash tools,
    so it modifies repos, produces diffs, and runs tests on its own — no
    external code agent required.

    The tool registry is built with ``auto_approve=True`` (EvoAgent's documented
    autonomous usage). This is essential: EvoAgent's ReAct loop runs tools
    synchronously inside ``agent.run()``, so ASK-classified commands (e.g. a
    harmless ``cd``) cannot be routed to the chat approval popup mid-loop —
    without auto-approve they would simply fail with "Permission required".
    Genuinely destructive commands are still blocked by the policy's DENY rules.
    Explicit high-risk intent is gated by the orchestrator's own approval flow.
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

    async def run_full(self, user_input: str) -> AgentRunResult:
        result = await self._agent.run(user_input)
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
                        metadata=dict(tr.metadata or {}),
                    )
                )
        return AgentRunResult(answer=answer, success=result.success, tool_calls=tool_calls)

    async def run(self, user_input: str) -> str:
        return (await self.run_full(user_input)).answer
