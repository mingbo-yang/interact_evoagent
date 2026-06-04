"""DiffRecorder — generate and save unified diffs for file changes."""

import difflib
from pathlib import Path


class DiffRecorder:
    """Records file diffs for traceability.

    Usage:
        recorder = DiffRecorder("/path/to/patches_dir")
        diff = recorder.record_diff("old content", "new content", "file.py", step_id="step_1")
        # diff saved to patches_dir/step_1_file.py.patch
    """

    def __init__(self, patches_dir: str | Path = ".runs/patches"):
        self.patches_dir = Path(patches_dir)
        self.patches_dir.mkdir(parents=True, exist_ok=True)

    def generate_diff(
        self,
        old_text: str,
        new_text: str,
        filename: str,
    ) -> str:
        """Generate a unified diff between old and new text.

        Args:
            old_text: Original content.
            new_text: Modified content.
            filename: Label for the diff header.

        Returns:
            Unified diff string, or empty string if no changes.
        """
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm="",
        )
        result = "\n".join(diff)
        return result

    def record_diff(
        self,
        old_text: str,
        new_text: str,
        filename: str,
        step_id: str = "",
    ) -> str | None:
        """Generate and save a diff to disk.

        Args:
            old_text: Original content.
            new_text: Modified content.
            filename: Name of the changed file (used in header and file naming).
            step_id: Optional step identifier.

        Returns:
            Diff string, or None if no changes.
        """
        diff = self.generate_diff(old_text, new_text, filename)
        if not diff:
            return None

        safe_name = filename.replace("/", "_").replace("..", "_")
        prefix = f"{step_id}_" if step_id else ""
        patch_path = self.patches_dir / f"{prefix}{safe_name}.patch"
        patch_path.write_text(diff, encoding="utf-8")
        return diff

    @staticmethod
    def contains_changes(diff_text: str) -> bool:
        """Check if diff text contains actual changes (+ or - lines)."""
        return any(line.startswith("+") or line.startswith("-") for line in diff_text.split("\n"))
