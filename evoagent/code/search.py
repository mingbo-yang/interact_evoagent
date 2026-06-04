"""CodeSearch — search text, symbols, and files in a repository."""

import subprocess
from pathlib import Path


class CodeSearch:
    """Search code in a repository.

    Supports text search (grep), symbol lookup, file glob, and file summarization.
    """

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()

    def search_text(self, pattern: str, glob: str | None = None, max_results: int = 50) -> str:
        """Grep for a pattern in the workspace."""
        cmd = ["grep", "-rn", "--color=never", "-I"]
        if glob:
            cmd.extend(["--include", glob])
        cmd.extend([pattern, str(self.workspace)])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            lines = proc.stdout.strip().split("\n")
            if len(lines) > max_results:
                return "\n".join(lines[:max_results]) + f"\n... ({len(lines)} total)"
            return proc.stdout.strip() or "(no matches)"
        except Exception as e:
            return f"Search error: {e}"

    def search_symbol(self, symbol: str) -> str:
        """Search for a class/function definition in Python files."""
        return self.search_text(symbol, glob="*.py")

    def find_files(self, pattern: str) -> list[str]:
        """Find files matching a glob pattern."""
        files = sorted(self.workspace.rglob(pattern))
        return [str(f.relative_to(self.workspace)) for f in files if f.is_file()]

    def summarize_file(self, path: str) -> str:
        """Return a summary of a file: path, lines, first 20 lines."""
        p = self.workspace / path
        if not p.exists():
            return f"File not found: {path}"
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            preview = "\n".join(lines[:20])
            if len(lines) > 20:
                preview += f"\n... ({len(lines)} lines total)"
            return f"File: {path}\nLines: {len(lines)}\n---\n{preview}"
        except Exception as e:
            return f"Error reading {path}: {e}"
