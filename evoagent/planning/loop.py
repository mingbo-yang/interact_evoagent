"""AgentLoop — orchestrates Plan → Execute → Critic → Revise → Finish."""


from evoagent.core.cost import CostSnapshot
from evoagent.core.result import AgentResult
from evoagent.core.state import RunStatus, RuntimeState
from evoagent.logging.trace import TraceRecorder
from evoagent.planning.critic import Critic
from evoagent.planning.executor import Executor
from evoagent.planning.planner import Planner
from evoagent.planning.reflector import Reflector
from evoagent.planning.schema import ActionType
from evoagent.tools.registry import ToolRegistry


class AgentLoop:
    """Core agent execution loop.

    Flow: Plan → Execute Step → Critic → (Revise | Continue) → Finish

    Stop conditions:
    - All steps completed (finish reached)
    - max_steps reached
    - max_reflections reached
    - Human intervention required
    - Unrecoverable error
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        planner: Planner,
        executor: Executor,
        critic: Critic,
        reflector: Reflector | None = None,
        trace_recorder: TraceRecorder | None = None,
        max_steps: int = 20,
        cost: CostSnapshot | None = None,
    ):
        self.tool_registry = tool_registry
        self.planner = planner
        self.executor = executor
        self.critic = critic
        self.reflector = reflector or Reflector()
        self.trace_recorder = trace_recorder
        self.max_steps = max_steps
        self.cost = cost or CostSnapshot()

    async def run(self, task: str, context: str = "") -> AgentResult:
        """Execute the full agent loop.

        Args:
            task: The user's task description.
            context: Optional context string (memories, docs) for the planner.

        Returns:
            AgentResult with final outcome.
        """
        if self.trace_recorder:
            run_id = self.trace_recorder.start_run(task)
        else:
            from evoagent.core.ids import generate_id
            run_id = generate_id("run")

        state = RuntimeState(run_id=run_id, task=task)

        try:
            # 1. Plan
            tools_schema = self.tool_registry.get_tool_schemas()
            plan = await self.planner.plan(task, tools_schema, context=context or "")
            state.plan = plan
            if self.trace_recorder:
                self.trace_recorder.save_state(state)

            # 2. Execute loop
            step_count = 0
            step_index = 0
            while step_index < len(plan.steps):
                step = plan.steps[step_index]
                step_count += 1
                if step_count > self.max_steps:
                    state.errors.append(f"Max steps ({self.max_steps}) reached.")
                    break

                # Execute
                result = await self.executor.execute_step(state, step)

                # Check if human intervention needed
                if state.status == RunStatus.WAITING_FOR_HUMAN:
                    break

                # 3. Critic
                decision = await self.critic.evaluate(task, step, result)

                if decision.passed:
                    if step.action_type == ActionType.FINISH:
                        break
                    step_index += 1
                    continue

                # 4. Reflect — revise plan if step failed
                revised = await self.reflector.reflect(task, step, decision, plan)
                if revised is None:
                    state.add_error(f"Max reflections reached for plan {plan.id}. Aborting.")
                    break
                plan = revised
                state.plan = plan
                # Restart execution from the beginning of the revised plan.
                step_index = 0
                if self.trace_recorder:
                    self.trace_recorder.save_state(state)

            # Finalize
            final_answer = self._build_final_answer(state)
            state.status = RunStatus.SUCCEEDED if not state.errors else RunStatus.FAILED
            if self.trace_recorder:
                self.trace_recorder.save_state(state)

            agent_result = AgentResult(
                run_id=run_id, task=task,
                success=state.status == RunStatus.SUCCEEDED,
                final_answer=final_answer, state=state,
                steps_taken=step_count,
                tool_calls=len(state.tool_results),
                total_tokens=self.cost.total_tokens,
                total_cost=self.cost.cost_usd,
                error="; ".join(state.errors) if state.errors else None,
            )

            if self.trace_recorder:
                self.trace_recorder.save_final_result(agent_result)

            return agent_result

        except Exception as e:
            state.add_error(str(e))
            state.status = RunStatus.FAILED
            return AgentResult(run_id=run_id, task=task, success=False,
                               final_answer="", state=state, error=str(e))

    def _build_final_answer(self, state: RuntimeState) -> str:
        """Build a final answer from the execution state.

        The FINISH step always produces a constant placeholder output, so it
        must not shadow the real answer. Prefer the last assistant message,
        then the last successful non-FINISH step output.
        """
        if state.messages:
            last = state.messages[-1]
            if last.content:
                return last.content
        for sr in reversed(state.step_results):
            step = self._find_step(state, sr.step_id)
            if step is not None and step.action_type == ActionType.FINISH:
                continue
            if sr.success and sr.output:
                return str(sr.output)
        return "Task completed."

    @staticmethod
    def _find_step(state: RuntimeState, step_id: str):
        """Resolve a step by id from the current plan, if available."""
        if state.plan:
            for s in state.plan.steps:
                if s.id == step_id:
                    return s
        return None
