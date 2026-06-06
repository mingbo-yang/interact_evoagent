"""Executor — execute a single PlanStep."""

from typing import Any

from evoagent.core.state import RunStatus, RuntimeState, StepResult
from evoagent.core.time import utc_now_iso
from evoagent.logging.event import EventType
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest
from evoagent.planning.prompts import EXECUTOR_SYSTEM_PROMPT
from evoagent.planning.schema import ActionType, PlanStep, StepStatus
from evoagent.tools.registry import ToolRegistry


class Executor:
    """Execute individual plan steps.

    Dispatches based on action_type:
    - tool → ToolRegistry.run_tool()
    - llm → LLM call for reasoning
    - code → python tool
    - ask_user → set waiting_for_human status
    - finish → mark complete
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm: BaseLLMProvider | None = None,
        event_logger: Any = None,
        cost: Any = None,
    ):
        self.tool_registry = tool_registry
        self.llm = llm
        self.event_logger = event_logger
        self.cost = cost

    async def execute_step(self, state: RuntimeState, step: PlanStep) -> StepResult:
        """Execute a plan step and update RuntimeState.

        Args:
            state: Current RuntimeState.
            step: The PlanStep to execute.

        Returns:
            StepResult with outcome.
        """
        state.current_step_id = step.id
        step.status = StepStatus.RUNNING
        state.status = RunStatus.RUNNING
        started_at = utc_now_iso()

        try:
            if step.action_type == ActionType.TOOL:
                result = await self._execute_tool(state, step)
            elif step.action_type == ActionType.LLM:
                result = await self._execute_llm(state, step)
            elif step.action_type == ActionType.CODE:
                result = await self._execute_code(state, step)
            elif step.action_type == ActionType.ASK_USER:
                result = self._execute_ask_user(state, step)
            elif step.action_type == ActionType.FINISH:
                result = self._execute_finish(state, step)
            else:
                result = StepResult(step_id=step.id, success=False, error=f"Unknown action_type: {step.action_type}")
        except Exception as e:
            result = StepResult(step_id=step.id, success=False, error=str(e), started_at=started_at, finished_at=utc_now_iso())

        step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
        step.result = result
        state.add_step_result(result)

        if self.event_logger:
            self.event_logger.log(EventType.RUN_FINISHED if step.action_type == ActionType.FINISH else EventType.TOOL_CALL_FINISHED,
                                  payload={"step_id": step.id, "success": result.success, "error": result.error})

        return result

    async def _execute_tool(self, state: RuntimeState, step: PlanStep) -> StepResult:
        tool_name = step.tool_name or ""
        try:
            tr = await self.tool_registry.run_tool(tool_name, step.arguments)
            state.add_tool_result(tr)
            return StepResult(step_id=step.id, success=tr.success, output=tr.output, error=tr.error)
        except Exception as e:
            return StepResult(step_id=step.id, success=False, error=str(e))

    async def _execute_llm(self, state: RuntimeState, step: PlanStep) -> StepResult:
        if not self.llm:
            return StepResult(step_id=step.id, success=False, error="No LLM provider configured for executor.")
        request = LLMRequest(
            messages=[
                {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Step: {step.goal}\nContext: {state.task}"},
            ],
        )
        response = await self.llm.chat(request)
        if self.cost is not None:
            usage = getattr(response, "usage", None) or {}
            self.cost.add_call(
                getattr(response, "model", "") or "",
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )
        return StepResult(step_id=step.id, success=True, output=response.content)

    async def _execute_code(self, state: RuntimeState, step: PlanStep) -> StepResult:
        code = step.arguments.get("code", "")
        if not code:
            return StepResult(step_id=step.id, success=False, error="No code provided for code step.")
        try:
            tr = await self.tool_registry.run_tool("python", {"code": code})
            state.add_tool_result(tr)
            return StepResult(step_id=step.id, success=tr.success, output=tr.output, error=tr.error)
        except Exception as e:
            return StepResult(step_id=step.id, success=False, error=str(e))

    def _execute_ask_user(self, state: RuntimeState, step: PlanStep) -> StepResult:
        state.status = RunStatus.WAITING_FOR_HUMAN
        return StepResult(step_id=step.id, success=True, output=step.goal)

    def _execute_finish(self, state: RuntimeState, step: PlanStep) -> StepResult:
        state.status = RunStatus.SUCCEEDED
        return StepResult(step_id=step.id, success=True, output="Task finished.")
