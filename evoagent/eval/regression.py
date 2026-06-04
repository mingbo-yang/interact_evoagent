"""Regression — compare evaluation reports and detect regressions."""

from evoagent.eval.metrics import Metrics
from evoagent.eval.task import EvalResult


class Regression:
    """Compare two evaluation runs and detect regressions.

    Usage:
        reg = Regression.compare(old_results, new_results)
        if reg["regression_detected"]:
            print(reg["warnings"])
    """

    @staticmethod
    def compare(old: list[EvalResult], new: list[EvalResult]) -> dict:
        """Compare old and new evaluation results.

        Returns a dict with regression_detected flag and warnings.
        """
        old_metrics = Metrics.compute(old)
        new_metrics = Metrics.compute(new)

        warnings: list[str] = []
        regression = False

        old_sr = old_metrics["success_rate"]
        new_sr = new_metrics["success_rate"]

        if new_sr < old_sr - 0.05:
            warnings.append(f"Success rate dropped from {old_sr:.1%} to {new_sr:.1%}")
            regression = True

        old_score = old_metrics["average_score"]
        new_score = new_metrics["average_score"]
        if new_score < old_score - 0.1:
            warnings.append(f"Average score dropped from {old_score:.2f} to {new_score:.2f}")
            regression = True

        # Check individual tasks
        old_by_id = {r.task_id: r for r in old}
        for r in new:
            if r.task_id in old_by_id:
                if not r.success and old_by_id[r.task_id].success:
                    warnings.append(f"Task '{r.task_id}' regressed from pass to fail.")
                    regression = True

        return {
            "regression_detected": regression,
            "warnings": warnings,
            "old_metrics": old_metrics,
            "new_metrics": new_metrics,
        }
