"""Critic — evaluate step results and decide next actions."""

import json
from dataclasses import dataclass
from typing import Any

from evoagent.logging.event import EventType
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest
from evoagent.planning.prompts import CRITIC_SYSTEM_PROMPT, CRITIC_USER_TEMPLATE
from evoagent.planning.schema import PlanStep


@dataclass
class CriticDecision:
    """Result of a critic evaluation."""

    passed: bool
    needs_revision: bool
    needs_more_info: bool
    reason: str
    suggested_action: str | None = None
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "needs_revision": self.needs_revision,
            "needs_more_info": self.needs_more_info,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
        }


class Critic:
    """Evaluate step execution results.

    Supports two modes:
    - LLM-based: uses ModelRouter critic role
    - Rule-based: simple heuristics (no LLM needed)
    """

    def __init__(
        self,
        llm: BaseLLMProvider | None = None,
        mode: str = "rule",
        event_logger: Any = None,
    ):
        self.llm = llm
        self.mode = mode
        self.event_logger = event_logger

    async def evaluate(
        self, task: str, step: PlanStep, result: Any
    ) -> CriticDecision:
        """Evaluate a step result.

        Args:
            task: The original task.
            step: The executed PlanStep.
            result: The StepResult or ToolResult.

        Returns:
            CriticDecision.
        """
        if self.mode == "llm" and self.llm:
            return await self._llm_evaluate(task, step, result)
        return self._rule_evaluate(task, step, result)

    async def _llm_evaluate(self, task: str, step: PlanStep, result: Any) -> CriticDecision:
        expected = step.expected_result or "step should complete successfully"
        actual = getattr(result, "output", str(result))
        error = getattr(result, "error", None)
        if error:
            actual = f"ERROR: {error}"

        user_msg = CRITIC_USER_TEMPLATE.format(
            task=task, step_goal=step.goal, expected=expected, actual=actual,
        )
        request = LLMRequest(messages=[
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
        response = await self.llm.chat(request)
        return self._parse_critic(response.content)

    def _rule_evaluate(self, task: str, step: PlanStep, result: Any) -> CriticDecision:
        success = getattr(result, "success", False)
        error = getattr(result, "error", None)

        if success:
            if self.event_logger:
                self.event_logger.log(EventType.CRITIC_FEEDBACK, payload={"step_id": step.id, "passed": True})
            return CriticDecision(passed=True, needs_revision=False, needs_more_info=False,
                                  reason="Step completed successfully.", confidence=1.0)

        reason = error or "Step failed with no error message."
        if self.event_logger:
            self.event_logger.log(EventType.CRITIC_FEEDBACK, payload={"step_id": step.id, "passed": False, "reason": reason})
        return CriticDecision(passed=False, needs_revision=True, needs_more_info=False,
                              reason=reason, suggested_action="Retry with corrected arguments.", confidence=0.3)

    def _parse_critic(self, content: str) -> CriticDecision:
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            return CriticDecision(passed=False, needs_revision=True, needs_more_info=True,
                                  reason="Failed to parse critic response.", confidence=0.0)
        return CriticDecision(
            passed=data.get("passed", False),
            needs_revision=data.get("needs_revision", False),
            needs_more_info=data.get("needs_more_info", False),
            reason=data.get("reason", ""),
            suggested_action=data.get("suggested_action"),
            confidence=data.get("confidence", 0.5),
        )
