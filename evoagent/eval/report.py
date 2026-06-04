"""EvalReport — generate and save evaluation reports (Markdown, JSON, CSV, comparison)."""

import csv
import io
import json
from pathlib import Path

from evoagent.eval.metrics import Metrics
from evoagent.eval.task import EvalResult


class EvalReport:
    """Generate evaluation reports in Markdown and JSON formats."""

    @staticmethod
    def summarize(results: list[EvalResult]) -> str:
        """Return a Markdown summary table."""
        metrics = Metrics.compute(results)
        lines = [
            "# Eval Report",
            "",
            f"**Total tasks**: {metrics['total']}",
            f"**Success rate**: {metrics['success_rate']:.1%}",
            f"**Average score**: {metrics['average_score']:.2f}",
            f"**Avg duration**: {metrics['avg_duration_ms']} ms",
            "",
            "## Task Results",
            "",
            "| Task ID | Success | Score | Duration | Error |",
            "|---------|---------|-------|----------|-------|",
        ]
        for r in results:
            err = (r.error or "")[:50]
            lines.append(f"| {r.task_id} | {'✅' if r.success else '❌'} | {r.score:.2f} | {r.duration_ms}ms | {err} |")
        return "\n".join(lines)

    @staticmethod
    def to_markdown(results: list[EvalResult]) -> str:
        return EvalReport.summarize(results)

    @staticmethod
    def to_json(results: list[EvalResult]) -> str:
        metrics = Metrics.compute(results)
        return json.dumps({"metrics": metrics, "results": [r.model_dump() for r in results]}, indent=2, ensure_ascii=False)

    @staticmethod
    def save_report(results: list[EvalResult], path: str | Path, fmt: str = "md") -> str:
        """Save report to a file.

        Args:
            results: List of EvalResult.
            path: Output file path.
            fmt: Format: 'md' or 'json'.

        Returns:
            The file path.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        content = EvalReport.to_markdown(results) if fmt == "md" else EvalReport.to_json(results)
        p.write_text(content, encoding="utf-8")
        return str(p)

    @staticmethod
    def to_csv(results: list[EvalResult]) -> str:
        """Export results as CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["task_id", "success", "score", "duration_ms", "error"])
        for r in results:
            writer.writerow([r.task_id, r.success, r.score, r.duration_ms, (r.error or "")[:100]])
        return output.getvalue()

    @staticmethod
    def compare(label_old: str, old: list[EvalResult], label_new: str, new: list[EvalResult]) -> str:
        """Generate a markdown comparison of two evaluation runs."""
        m_old = Metrics.compute(old)
        m_new = Metrics.compute(new)
        lines = [
            f"# Eval Comparison: {label_old} vs {label_new}",
            "",
            "| Metric | {label_old} | {label_new} | Change |",
            "|--------|------------|------------|--------|",
        ]
        for key in ["total", "success_rate", "average_score", "avg_duration_ms"]:
            ov = m_old.get(key, 0)
            nv = m_new.get(key, 0)
            if isinstance(ov, float):
                change = f"{nv - ov:+.1%}" if key == "success_rate" else f"{nv - ov:+.2f}"
            else:
                change = f"{nv - ov:+d}" if isinstance(nv, int) else "-"
            lines.append(f"| {key} | {ov} | {nv} | {change} |")
        return "\n".join(lines)
