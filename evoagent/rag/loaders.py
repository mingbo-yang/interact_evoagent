"""Document loaders — TextLoader and DirectoryLoader."""

from pathlib import Path

from evoagent.rag.document import Document

# File extensions we can load as text
_TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                    ".toml", ".cfg", ".ini", ".sh", ".bash", ".html", ".css",
                    ".csv", ".xml", ".rst", ".sql", ".java", ".go", ".rs", ".c", ".cpp", ".h"}

# Directories to skip
_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}


class TextLoader:
    """Load a single text file as a Document."""

    def __init__(self, max_size_mb: int = 10):
        self.max_size = max_size_mb * 1024 * 1024

    def load(self, path: str | Path) -> Document | None:
        p = Path(path)
        if not p.is_file():
            return None
        if p.stat().st_size > self.max_size:
            return None  # Skip oversized files
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
        return Document(text=text, source=str(p), metadata={"filename": p.name, "suffix": p.suffix})


class DirectoryLoader:
    """Recursively load text files from a directory."""

    def __init__(self, max_size_mb: int = 10):
        self.txt_loader = TextLoader(max_size_mb=max_size_mb)

    def load(self, path: str | Path) -> list[Document]:
        root = Path(path)
        docs: list[Document] = []
        if not root.is_dir():
            return docs
        for p in sorted(root.rglob("*")):
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if not p.is_file():
                continue
            if p.suffix.lower() not in _TEXT_EXTENSIONS:
                continue
            doc = self.txt_loader.load(p)
            if doc:
                docs.append(doc)
        return docs
