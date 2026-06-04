"""PatchManager — generate, apply, and track file changes."""

import subprocess
from pathlib import Path


class PatchManager:
    """Manages file patches: generation, tracking, and rollback.

    Uses git when available, falls back to manual diff.
    """

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()
        self._patch_backups: dict[str, str] = {}

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """Edit a file by replacing text. Backs up original for rollback.

        Returns:
            A description of what was done.
        """
        p = self.workspace / path
        if not p.exists():
            return f"File not found: {path}"
        content = p.read_text(encoding="utf-8")
        if old_text not in content:
            return f"old_text not found in {path}"
        # Backup original
        self._patch_backups[str(p)] = content
        new_content = content.replace(old_text, new_text)
        p.write_text(new_content, encoding="utf-8")
        count = content.count(old_text)
        return f"Replaced {count} occurrence(s) in {path}"

    def write_file(self, path: str, content: str) -> str:
        """Write a new file or overwrite existing (backs up original)."""
        p = self.workspace / path
        if p.exists():
            self._patch_backups[str(p)] = p.read_text(encoding="utf-8")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {path}"

    def get_diff(self) -> str:
        """Get the current git diff, or fallback to listing changed files."""
        try:
            proc = subprocess.run(
                ["git", "diff"], capture_output=True, text=True, timeout=10,
                cwd=str(self.workspace),
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass
        # Fallback: list changed files from backups
        if self._patch_backups:
            return "Changed files:\n" + "\n".join(self._patch_backups.keys())
        return "(no changes tracked)"

    def changed_files(self) -> list[str]:
        """List files that were modified via this PatchManager."""
        return list(self._patch_backups.keys())

    def rollback_last(self) -> str:
        """Rollback the most recent patch (last file edited)."""
        if not self._patch_backups:
            return "No patches to rollback."
        path, content = self._patch_backups.popitem()
        Path(path).write_text(content, encoding="utf-8")
        return f"Rolled back: {path}"
