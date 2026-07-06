from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evoagent.cli.utils import create_agent


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
    """Thin wrapper around EvoAgent that also surfaces its internal tool calls.

    EvoAgent already has native file-edit / patch / run_tests / git_diff tools,
    so it can modify a repo, produce diffs, and run tests on its own — no
    external code agent (Codex/Claude Code) is required. We expose the tool
    calls it made so they can be rendered in the workflow visualization.
    """

    def __init__(self):
        self._agent = create_agent(mock=False)

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

