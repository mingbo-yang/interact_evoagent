"""Subagent orchestration — a parallel ``task`` tool.

The ``task`` tool lets an orchestrator agent delegate one or more independent
sub-tasks to fresh sub-agents that run concurrently (``asyncio.gather``). Each
sub-agent gets its own ReAct loop and a fresh tool registry on the same
workspace, but **without** the ``task`` tool itself, so sub-agents cannot spawn
further sub-agents (depth is capped at 1). Sub-agents auto-approve ASK actions
(deny rules still apply) and are bounded by ``max_steps``.
"""

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from evoagent.core.ids import generate_id
from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.schema import ToolResult

_MAX_PARALLEL = 5


class SubTask(BaseModel):
    description: str = Field(..., description="Short label for the sub-task.")
    prompt: str = Field(..., description="Full instructions for the sub-agent.")


class TaskInput(BaseModel):
    tasks: list[SubTask] = Field(
        ...,
        description="One or more independent sub-tasks to run in parallel.",
        min_length=1,
    )
    max_steps: int = Field(
        default=20, ge=1, le=100,
        description="Max ReAct steps allowed per sub-agent.",
    )


class SubagentTool(BaseTool):
    name = "task"
    description = (
        "Delegate one or more independent sub-tasks to fresh sub-agents that run "
        "in parallel, each with its own tools and context window. Use this to "
        "decompose a large task into independent pieces (e.g. investigate "
        "several modules at once) and collect their results. Each sub-task needs "
        "a short description and a complete, self-contained prompt."
    )
    input_schema = TaskInput
    risk_level = RiskLevel.MEDIUM
    # Sub-agent transcripts can be large; rely on per-sub-agent answers only.
    max_output_chars = 30_000

    def __init__(self, workspace: Path, model_router: Any, permission_policy: Any = None):
        self.workspace = workspace
        self.model_router = model_router
        self.permission_policy = permission_policy

    async def run(self, tasks: list, max_steps: int = 20) -> ToolResult:
        # Pydantic validation gives us SubTask models; tolerate dicts too.
        norm: list[SubTask] = [
            t if isinstance(t, SubTask) else SubTask.model_validate(t) for t in tasks
        ]
        sem = asyncio.Semaphore(_MAX_PARALLEL)

        async def _one(task: SubTask) -> tuple[str, bool, str]:
            async with sem:
                try:
                    answer, ok = await self._run_subagent(task.prompt, max_steps)
                    return task.description, ok, answer
                except Exception as e:  # never let one sub-agent crash the batch
                    return task.description, False, f"Sub-agent error: {e}"

        results = await asyncio.gather(*(_one(t) for t in norm))
        blocks: list[str] = []
        all_ok = True
        for i, (desc, ok, answer) in enumerate(results, 1):
            status = "ok" if ok else "FAILED"
            all_ok = all_ok and ok
            blocks.append(f"### Subtask {i}: {desc} [{status}]\n{answer}")
        return ToolResult(
            call_id=generate_id("call"), name=self.name, success=all_ok,
            output="\n\n".join(blocks),
            metadata={"subtasks": len(norm), "all_ok": all_ok},
        )

    async def _run_subagent(self, prompt: str, max_steps: int) -> tuple[str, bool]:
        # Imported lazily to avoid a circular import (builtin -> subagent_tools).
        from evoagent.core.cost import CostSnapshot
        from evoagent.core.message import Message, MessageRole
        from evoagent.core.react import ReActEngine
        from evoagent.sandbox.policy import PermissionPolicy
        from evoagent.tools.builtin import create_builtin_registry

        # Fresh registry WITHOUT the task tool → sub-agents cannot recurse.
        registry = create_builtin_registry(
            self.workspace, auto_approve=True, enable_subagents=False
        )
        engine = ReActEngine(
            model_router=self.model_router,
            tool_registry=registry,
            permission_policy=self.permission_policy or PermissionPolicy(),
            role="executor",
            cost=CostSnapshot(),
            ask_fallback="allow",
            max_steps=max_steps,
            max_tool_rounds=max_steps,
        )
        system_prompt = (
            "You are a focused sub-agent. Complete ONLY the assigned sub-task "
            "using the available tools, then reply with a concise final answer. "
            f"You are working in the workspace at '{self.workspace}'."
        )
        messages = [Message(role=MessageRole.USER, content=prompt)]
        result = await engine.run_turn(messages, system_prompt=system_prompt)
        return result.final_text, result.success
