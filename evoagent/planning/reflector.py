"""Reflector — revise plans based on critic feedback."""

import json
from typing import Any

from evoagent.core.ids import generate_id
from evoagent.logging.event import EventType
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest
from evoagent.planning.critic import CriticDecision
from evoagent.planning.prompts import REFLECTOR_SYSTEM_PROMPT
from evoagent.planning.schema import ActionType, Plan, PlanStep


class Reflector:
    """Revise plans when steps fail.

    Limits the number of reflection rounds to prevent infinite loops.
    """

    def __init__(
        self,
        llm: BaseLLMProvider | None = None,
        max_reflections: int = 3,
        event_logger: Any = None,
    ):
        self.llm = llm
        self.max_reflections = max_reflections
        self.event_logger = event_logger
        self._reflection_count: dict[str, int] = {}

    async def reflect(
        self,
        task: str,
        failed_step: PlanStep,
        decision: CriticDecision,
        plan: Plan,
    ) -> Plan | None:
        """Revise a plan after a step failure.

        Args:
            task: The original task.
            failed_step: The step that failed.
            decision: Critic feedback.
            plan: The current plan.

        Returns:
            Revised Plan, or None if no revision is possible.
        """
        plan_id = plan.id
        count = self._reflection_count.get(plan_id, 0)
        if count >= self.max_reflections:
            return None
        self._reflection_count[plan_id] = count + 1

        if self.llm:
            return await self._llm_reflect(task, failed_step, decision, plan)
        return self._rule_reflect(task, failed_step, plan)

    async def _llm_reflect(
        self, task: str, step: PlanStep, decision: CriticDecision, plan: Plan
    ) -> Plan | None:
        user_msg = f"Task: {task}\nFailed step: {step.goal}\nError: {decision.reason}\nCurrent plan: {[s.goal for s in plan.steps]}"
        request = LLMRequest(messages=[
            {"role": "system", "content": REFLECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
        response = await self.llm.chat(request)
        try:
            data = json.loads(response.content.strip())
        except json.JSONDecodeError:
            return None

        revised_steps = data.get("revised_steps", [])
        if not revised_steps:
            return None

        steps = []
        for s in revised_steps:
            steps.append(PlanStep(
                goal=s.get("goal", "Revised step"),
                action_type=ActionType(s.get("action_type", "tool")),
                tool_name=s.get("tool_name"),
                arguments=s.get("arguments", {}),
                expected_result=s.get("expected_result"),
            ))
        if not steps or steps[-1].action_type != ActionType.FINISH:
            steps.append(PlanStep(goal="Finish", action_type=ActionType.FINISH))

        if self.event_logger:
            self.event_logger.log(EventType.PLAN_UPDATED, payload={"plan_id": plan.id})

        return Plan(id=generate_id("plan"), task=task, steps=steps)

    def _rule_reflect(self, task: str, step: PlanStep, plan: Plan) -> Plan | None:
        """Rule-based reflection with intelligent recovery.

        Generates recovery steps based on the error pattern:
        - unknown tool → list tools + try correct name
        - file not found → list directory + search
        - permission denied → ask_user for approval
        - shell/test failed → read error + retry targeted command
        """
        error = ""
        if step.result and hasattr(step.result, "error") and step.result.error:
            error = str(step.result.error).lower()

        recovery_steps: list[PlanStep] = []

        if "unknown tool" in error or "tool not found" in error:
            recovery_steps.append(PlanStep(
                goal="List available tools to find correct tool name",
                action_type=ActionType.TOOL, tool_name="list_directory",
                arguments={"path": "."}, expected_result="See what tools are available",
            ))
        elif "file not found" in error or "no such file" in error:
            recovery_steps.append(PlanStep(
                goal="List directory to find correct file path",
                action_type=ActionType.TOOL, tool_name="list_directory",
                arguments={"path": "."}, expected_result="Find correct file location",
            ))
        elif "permission denied" in error:
            recovery_steps.append(PlanStep(
                goal="Request user approval for this action",
                action_type=ActionType.ASK_USER,
                expected_result="Get user approval or alternative path",
            ))
        elif "exit code" in error or "failed" in error:
            recovery_steps.append(PlanStep(
                goal="Inspect the error and retry with corrected command",
                action_type=ActionType.TOOL, tool_name="bash",
                arguments={"command": "echo 'Diagnostic: check error output'"},
                expected_result="Understand what went wrong and retry with fix",
            ))
        else:
            # Generic: inspect and retry
            recovery_steps.append(PlanStep(
                goal=f"Recover from error: {error[:100]}",
                action_type=ActionType.LLM,
                expected_result="Analyze error and determine next action",
            ))

        # Build revised plan: keep remaining steps + recovery + finish
        remaining = [s for s in plan.steps if s.id != step.id and s.action_type != ActionType.FINISH]
        all_steps = recovery_steps + remaining
        all_steps.append(PlanStep(goal="Finish after recovery", action_type=ActionType.FINISH))
        return Plan(id=generate_id("plan"), task=task, steps=all_steps)
