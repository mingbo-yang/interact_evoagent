"""CodeSearch — search text, symbols, and files in a repository."""

import re
import subprocess
from pathlib import Path


class CodeSearch:
    """Search code in a repository.

    Supports text search (grep), symbol lookup, file glob, and file summarization.
    """

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()

    def _iter_files(self, glob: str | None):
        pattern = glob or "*"
        for path in self.workspace.rglob(pattern):
            if path.is_file():
                yield path

    def _search_text_fallback(self, pattern: str, glob: str | None, max_results: int) -> str:
        try:
            rgx = re.compile(pattern)
        except re.error as e:
            return f"Search error: invalid regex pattern: {e}"

        matches: list[str] = []
        for path in self._iter_files(glob):
            try:
                with path.open("r", encoding="utf-8", errors="replace") as f:
                    for line_no, line in enumerate(f, 1):
                        if rgx.search(line):
                            rel = path.relative_to(self.workspace)
                            matches.append(f"{rel}:{line_no}:{line.rstrip()}")
                            if len(matches) >= max_results:
                                return "\n".join(matches) + f"\n... ({len(matches)}+ matches)"
            except OSError:
                continue
        return "\n".join(matches) if matches else "(no matches)"

    def search_text(self, pattern: str, glob: str | None = None, max_results: int = 50) -> str:
        """Search for regex pattern in the workspace with portable fallback."""
        cmd = ["rg", "-n", "--color=never", "--no-heading", "-I"]
        if glob:
            cmd.extend(["-g", glob])
        cmd.extend([pattern, str(self.workspace)])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            out = proc.stdout.strip()
            if proc.returncode in (0, 1):  # 1 = no matches for rg
                lines = out.splitlines() if out else []
                if len(lines) > max_results:
                    return "\n".join(lines[:max_results]) + f"\n... ({len(lines)} total)"
                return out or "(no matches)"
        except Exception:
            pass
        return self._search_text_fallback(pattern, glob, max_results)

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
