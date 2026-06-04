"""Metrics — compute aggregate statistics from EvalResults."""

import statistics

from evoagent.eval.task import EvalResult


class Metrics:
    """Compute evaluation metrics from a list of EvalResults."""

    @staticmethod
    def compute(results: list[EvalResult]) -> dict:
        """Compute all metrics from a list of results.

        Returns a dict with success_rate, average_score, avg_duration_ms,
        avg_steps, avg_tool_calls, avg_llm_calls, avg_errors, pass_rate.
        Unavailable metrics return None.
        """
        if not results:
            return {
                "total": 0, "success_rate": 0.0, "average_score": 0.0,
                "avg_duration_ms": 0, "avg_steps": None, "avg_tool_calls": None,
                "avg_llm_calls": None, "avg_errors": None,
                "pass_rate": 0.0, "memory_hit_rate": None,
                "recovery_success_rate": None,
            }

        total = len(results)
        success_count = sum(1 for r in results if r.success)
        scores = [r.score for r in results]
        durations = [r.duration_ms for r in results if r.duration_ms > 0]

        def safe_avg(key: str) -> float | None:
            vals = [r.metrics.get(key, 0) for r in results if key in r.metrics]
            return statistics.mean(vals) if vals else None

        return {
            "total": total,
            "success_rate": success_count / total if total else 0.0,
            "average_score": statistics.mean(scores) if scores else 0.0,
            "avg_duration_ms": int(statistics.mean(durations)) if durations else 0,
            "avg_steps": safe_avg("steps"),
            "avg_tool_calls": safe_avg("tool_calls"),
            "avg_llm_calls": safe_avg("llm_calls"),
            "avg_errors": safe_avg("errors"),
            "pass_rate": success_count / total if total else 0.0,
            "memory_hit_rate": safe_avg("memory_hit_rate"),
            "recovery_success_rate": safe_avg("recovery_success_rate"),
            "total_cost_usd": round(sum(r.cost_usd for r in results), 6),
            "avg_cost_usd": round(statistics.mean([r.cost_usd for r in results]) if results else 0.0, 6),
        }
