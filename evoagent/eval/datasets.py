"""DatasetLoader — load and save EvalTask JSONL files."""

import json
from pathlib import Path

from evoagent.eval.task import EvalTask


class DatasetLoader:
    """Load and validate EvalTask datasets in JSONL format.

    Format: one JSON object per line, each matching EvalTask schema.
    """

    @staticmethod
    def load_jsonl(path: str | Path) -> list[EvalTask]:
        """Load tasks from a JSONL file.

        Args:
            path: Path to .jsonl file.

        Returns:
            List of validated EvalTask objects.

        Raises:
            ValueError: If any line fails validation.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")
        tasks: list[EvalTask] = []
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    tasks.append(EvalTask.model_validate(data))
                except Exception as e:
                    raise ValueError(f"Line {i} in {path} is invalid: {e}") from e
        return tasks

    @staticmethod
    def save_jsonl(tasks: list[EvalTask], path: str | Path) -> None:
        """Save tasks to a JSONL file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for task in tasks:
                f.write(json.dumps(task.model_dump(mode="json"), ensure_ascii=False) + "\n")

    @staticmethod
    def validate(tasks: list[EvalTask]) -> list[str]:
        """Validate a list of tasks. Returns warnings for potential issues."""
        warnings: list[str] = []
        ids = set()
        for task in tasks:
            if task.task_id in ids:
                warnings.append(f"Duplicate task_id: {task.task_id}")
            ids.add(task.task_id)
            if not task.expected_check and not task.test_command and not task.expected_output:
                warnings.append(f"Task {task.task_id} has no check method.")
        return warnings
