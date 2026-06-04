"""RepoMap — scan a code repository and extract structure."""

import ast
from pathlib import Path

from pydantic import BaseModel, Field

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".eggs", ".pytest_cache"}
TEXT_EXTS = {".py", ".js", ".ts", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh"}


class FileInfo(BaseModel):
    path: str
    language: str = ""
    lines: int = 0
    size_bytes: int = 0


class RepoSummary(BaseModel):
    root: str
    file_count: int = 0
    files: list[FileInfo] = Field(default_factory=list)
    truncated: bool = False


class RepoMap:
    """Scanner that builds a structural map of a code repository.

    Ignores .git, __pycache__, .venv, node_modules, dist, build.
    Extracts Python class/function names using ast.
    Limits to max_files (default 200) and max_size (10 MB per file).
    """

    def __init__(self, max_files: int = 200, max_size_mb: int = 10):
        self.max_files = max_files
        self.max_size = max_size_mb * 1024 * 1024

    def scan(self, root: str | Path) -> RepoSummary:
        root = Path(root).resolve()
        summary = RepoSummary(root=str(root))
        count = 0

        for p in sorted(root.rglob("*")):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if not p.is_file():
                continue
            if p.suffix.lower() not in TEXT_EXTS:
                continue
            if p.stat().st_size > self.max_size:
                continue
            count += 1
            if count > self.max_files:
                summary.truncated = True
                break
            try:
                lines = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
            except Exception:
                lines = 0
            lang = self._guess_lang(p.suffix)
            summary.files.append(FileInfo(path=str(p.relative_to(root)), language=lang, lines=lines, size_bytes=p.stat().st_size))
            summary.file_count = len(summary.files)
        return summary

    def extract_symbols(self, file_path: str | Path) -> list[str]:
        """Extract top-level class and function names from a Python file."""
        p = Path(file_path)
        if p.suffix != ".py":
            return []
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, Exception):
            return []
        symbols: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append(f"def {node.name}")
            elif isinstance(node, ast.ClassDef):
                symbols.append(f"class {node.name}")
        return symbols

    def summarize(self, root: str | Path) -> str:
        """Return a human-readable repo summary."""
        summary = self.scan(root)
        lines = [f"Repository: {summary.root}", f"Files: {summary.file_count}"]
        if summary.truncated:
            lines.append("(truncated)")
        for f in summary.files[:50]:
            lines.append(f"  {f.path}  ({f.language}, {f.lines}L, {f.size_bytes}B)")
        return "\n".join(lines)

    @staticmethod
    def _guess_lang(suffix: str) -> str:
        return {".py": "python", ".js": "javascript", ".ts": "typescript", ".md": "markdown",
                ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".sh": "shell"}.get(suffix, suffix.lstrip("."))
