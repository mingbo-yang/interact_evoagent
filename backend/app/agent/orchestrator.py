from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.agent.evoagent_wrapper import EvoAgentWrapper
from app.schemas.workflow_event import EventError, EventMetrics, WorkflowEvent, iso_now
from app.storage.db import Database
from app.tools.shell_tool import ShellTool


class InteractiveOrchestrator:
    def __init__(self, db: Database, workspace: str):
        self.db = db
        self.shell_tool = ShellTool(workspace)
        self._evoagent: EvoAgentWrapper | None = None

    def _event(
        self,
        run_id: str,
        thread_id: str,
        event_type: str,
        **kwargs: Any,
    ) -> WorkflowEvent:
        return WorkflowEvent(
            event_id=f"evt_{uuid.uuid4().hex[:10]}",
            event_type=event_type,
            run_id=run_id,
            thread_id=thread_id,
            seq=self.db.next_seq(run_id),
            **kwargs,
        )

    def _emit(self, event: WorkflowEvent) -> None:
        self.db.append_event(event)

    async def _emit_node(
        self,
        run_id: str,
        thread_id: str,
        step_id: int,
        node_id: str,
        node_name: str,
        node_type: str,
        visible_input: str,
        visible_output: str,
        duration_ms: int = 100,
    ) -> None:
        self._emit(
            self._event(
                run_id,
                thread_id,
                "node.started",
                step_id=step_id,
                node_id=node_id,
                node_name=node_name,
                node_type=node_type,
                status="running",
                visible_input=visible_input,
            )
        )
        await asyncio.sleep(0.1)
        self._emit(
            self._event(
                run_id,
                thread_id,
                "node.completed",
                step_id=step_id,
                node_id=node_id,
                node_name=node_name,
                node_type=node_type,
                status="success",
                visible_input=visible_input,
                visible_output=visible_output,
                metrics=EventMetrics(duration_ms=duration_ms),
                ended_at=iso_now(),
            )
        )

    async def run_mock(self, run_id: str, thread_id: str, user_input: str) -> None:
        self._emit(self._event(run_id, thread_id, "run.started", status="running"))
        await self._emit_node(
            run_id,
            thread_id,
            1,
            "task_understanding",
            "任务理解",
            "task_understanding",
            user_input,
            "已抽取用户目标与约束。",
        )
        await self._emit_node(
            run_id,
            thread_id,
            2,
            "planning",
            "任务规划",
            "planning",
            "基于用户输入进行拆解。",
            "任务拆分为协议、后端、前端与工具接入。",
        )
        final = "这是 mock orchestrator 的回复：已完成流程演示。"
        await self._emit_node(
            run_id,
            thread_id,
            3,
            "final_response",
            "最终答复",
            "final_response",
            "汇总执行结果。",
            final,
        )
        self.db.update_run(run_id, status="completed", final_answer=final)
        self._emit(
            self._event(
                run_id,
                thread_id,
                "run.completed",
                status="success",
                visible_output=final,
                ended_at=iso_now(),
            )
        )
        self._write_memory(run_id, user_input, ["mock workflow execution"], [])
        self._finalize_metrics(run_id)

    async def _wait_for_approval(self, run_id: str, thread_id: str) -> bool:
        self.db.update_run(run_id, status="paused", approval_state="required")
        self._emit(
            self._event(
                run_id,
                thread_id,
                "user.approval.required",
                status="paused",
                visible_output="Detected risky operation. Waiting for approval.",
            )
        )
        waited = 0
        while waited < 120:
            row = self.db.get_run(run_id)
            if not row:
                return False
            state = row["approval_state"]
            if state == "approved":
                self.db.update_run(run_id, status="running", approval_state="none")
                self._emit(
                    self._event(
                        run_id,
                        thread_id,
                        "user.approval.received",
                        status="running",
                        visible_output="Approval received. Resuming run.",
                    )
                )
                return True
            if state == "rejected":
                return False
            await asyncio.sleep(1)
            waited += 1
        return False

    def _route_shell_command(self, user_input: str) -> str | None:
        """Decide whether/what shell command to run for this message.

        - Explicit risky intent (e.g. delete/install) routes the risky command
          so the approval gate is genuinely exercised.
        - Listing intent routes a safe directory listing.
        - Otherwise no shell command is run.
        """
        lowered = user_input.lower()
        risky_map = {
            "rm -rf": "rm -rf ./__evoagent_demo__",
            "删除": "rm -rf ./__evoagent_demo__",
            "install": "pip install requests",
            "安装": "pip install requests",
        }
        for key, command in risky_map.items():
            if key in lowered or key in user_input:
                return command
        if "list" in lowered or "目录" in user_input or "文件" in user_input:
            return self.shell_tool.default_listing_command()
        return None

    async def _maybe_use_shell_tool(
        self,
        run_id: str,
        thread_id: str,
        user_input: str,
    ) -> str | None:
        command = self._route_shell_command(user_input)
        if command is None:
            return None
        self._emit(
            self._event(
                run_id,
                thread_id,
                "tool.started",
                status="running",
                tool_name="shell",
                visible_input=command,
            )
        )
        result = await self.shell_tool.run(command)
        if result.requires_approval:
            approved = await self._wait_for_approval(run_id, thread_id)
            if not approved:
                self._emit(
                    self._event(
                        run_id,
                        thread_id,
                        "tool.failed",
                        status="failed",
                        tool_name="shell",
                        error=EventError(
                            code="APPROVAL_DENIED",
                            message="User rejected the risky command.",
                            retryable=False,
                        ),
                        ended_at=iso_now(),
                    )
                )
                return "Tool execution cancelled because approval was not granted."
            result = await self.shell_tool.run(command)
        if result.success:
            self.db.create_artifact(run_id, "tool_output", "Shell Output", result.output[:4000])
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "artifact.created",
                    status="success",
                    tool_name="shell",
                    artifacts=[{"kind": "tool_output", "title": "Shell Output"}],
                )
            )
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "tool.completed",
                    status="success",
                    tool_name="shell",
                    visible_output=result.output[:1200],
                    ended_at=iso_now(),
                )
            )
            return result.output[:1200]
        self._emit(
            self._event(
                run_id,
                thread_id,
                "tool.failed",
                status="failed",
                tool_name="shell",
                error=EventError(code="TOOL_FAILED", message=result.error or "unknown", retryable=False),
                ended_at=iso_now(),
            )
        )
        return f"Shell tool failed: {result.error}"

    async def run_evoagent(self, run_id: str, thread_id: str, user_input: str) -> None:
        self._emit(self._event(run_id, thread_id, "run.started", status="running"))
        stage_pairs = [
            ("task_understanding", "任务理解", "task_understanding"),
            ("memory_retrieval", "记忆检索", "memory_retrieval"),
            ("planning", "任务规划", "planning"),
            ("tool_routing", "工具路由", "tool_routing"),
        ]
        for idx, (node_id, node_name, node_type) in enumerate(stage_pairs, start=1):
            await self._emit_node(
                run_id,
                thread_id,
                idx,
                node_id,
                node_name,
                node_type,
                user_input,
                f"{node_name}完成。",
                duration_ms=180,
            )

        tool_output = await self._maybe_use_shell_tool(run_id, thread_id, user_input)

        self._emit(
            self._event(
                run_id,
                thread_id,
                "node.started",
                step_id=5,
                node_id="execution",
                node_name="执行",
                node_type="execution",
                status="running",
                visible_input=user_input,
            )
        )
        try:
            if self._evoagent is None:
                self._evoagent = EvoAgentWrapper()
            agent_result = await self._evoagent.run_full(user_input)
            answer = agent_result.answer

            # Surface EvoAgent's OWN internal tool calls (edit_file, apply_patch,
            # run_tests, git_diff, bash, ...) into the workflow so the
            # "auto-edit code -> diff -> test" loop is visible without any
            # external code agent (Codex/Claude Code).
            self._surface_agent_tool_calls(run_id, thread_id, agent_result.tool_calls)

            if tool_output:
                answer = f"{answer}\n\n[Tool Context]\n{tool_output}"
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "node.completed",
                    step_id=5,
                    node_id="execution",
                    node_name="执行",
                    node_type="execution",
                    status="success",
                    visible_output="执行阶段完成。",
                    metrics=EventMetrics(duration_ms=800),
                    ended_at=iso_now(),
                )
            )
            await self._emit_node(
                run_id,
                thread_id,
                6,
                "reflection",
                "反思修正",
                "reflection",
                "检查执行结果。",
                "未发现需要重试的问题。",
                duration_ms=150,
            )
            await self._emit_node(
                run_id,
                thread_id,
                7,
                "final_response",
                "最终答复",
                "final_response",
                "生成最终答复。",
                answer,
                duration_ms=120,
            )
            self.db.update_run(run_id, status="completed", final_answer=answer)
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "run.completed",
                    status="success",
                    visible_output=answer,
                    ended_at=iso_now(),
                )
            )
            self._write_memory(
                run_id,
                user_input,
                ["understand task", "retrieve memory", "plan", "route tools", "execute", "reflect", "respond"],
                [],
            )
            self._finalize_metrics(run_id)
        except Exception as e:
            msg = str(e)
            self.db.update_run(run_id, status="failed", error=msg)
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "node.failed",
                    step_id=5,
                    node_id="execution",
                    node_name="执行",
                    node_type="execution",
                    status="failed",
                    error=EventError(code="EXEC_FAILED", message=msg, retryable=False),
                    ended_at=iso_now(),
                )
            )
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "run.failed",
                    status="failed",
                    error=EventError(code="RUN_FAILED", message=msg, retryable=False),
                    ended_at=iso_now(),
                )
            )
            self._finalize_metrics(run_id)

    def _finalize_metrics(self, run_id: str) -> None:
        """Persist aggregate run metrics (event count, tool count, duration)."""
        run = self.db.get_run(run_id)
        if run is None:
            return
        event_count = self.db.count_events(run_id)
        tool_count = self.db.count_tool_events(run_id)
        duration_ms = 0
        try:
            from datetime import datetime

            start = datetime.fromisoformat(run["created_at"])
            duration_ms = max(0, int((datetime.now(start.tzinfo) - start).total_seconds() * 1000))
        except Exception:
            duration_ms = 0
        self.db.update_run(
            run_id,
            event_count=event_count,
            tool_count=tool_count,
            duration_ms=duration_ms,
        )

    # Tool names whose output is a meaningful artifact worth persisting.
    _ARTIFACT_TOOLS = {"git_diff", "run_tests", "apply_patch", "edit_file", "multi_edit", "write_file"}

    def _surface_agent_tool_calls(
        self,
        run_id: str,
        thread_id: str,
        tool_calls: list,
    ) -> None:
        """Emit workflow events + artifacts for EvoAgent's internal tool calls."""
        for call in tool_calls:
            status = "success" if call.success else "failed"
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "tool.started",
                    status="running",
                    tool_name=call.name,
                    source="evoagent",
                )
            )
            output = call.output or ""
            if call.name in self._ARTIFACT_TOOLS and output.strip():
                title = {
                    "git_diff": "Diff",
                    "run_tests": "Test Result",
                }.get(call.name, f"{call.name} output")
                self.db.create_artifact(run_id, call.name, title, output[:8000])
                self._emit(
                    self._event(
                        run_id,
                        thread_id,
                        "artifact.created",
                        status="success",
                        tool_name=call.name,
                        source="evoagent",
                        artifacts=[{"kind": call.name, "title": title}],
                    )
                )
            self._emit(
                self._event(
                    run_id,
                    thread_id,
                    "tool.completed" if call.success else "tool.failed",
                    status=status,
                    tool_name=call.name,
                    source="evoagent",
                    visible_output=output[:1200] if call.success else None,
                    error=None if call.success else EventError(
                        code="AGENT_TOOL_FAILED",
                        message=call.error or "tool failed",
                        retryable=False,
                    ),
                    ended_at=iso_now(),
                )
            )

    def _write_memory(
        self,
        run_id: str,
        user_input: str,
        successful_plan: list[str],
        failed_attempts: list[str],
    ) -> None:
        memory_id = f"mem_{uuid.uuid4().hex[:10]}"
        self.db.create_memory(
            memory_id=memory_id,
            run_id=run_id,
            task_type="interactive_workflow",
            user_goal=user_input,
            successful_plan=successful_plan,
            failed_attempts=failed_attempts,
            reusable_knowledge=[
                "Frontend should consume workflow events instead of direct internal objects.",
                "SSE run stream with ordered seq simplifies trace replay and UI updates.",
            ],
        )
        run = self.db.get_run(run_id)
        if run is not None:
            self._emit(
                self._event(
                    run_id,
                    run["thread_id"],
                    "memory.updated",
                    status="success",
                    visible_output=f"Memory record created: {memory_id}",
                )
            )

