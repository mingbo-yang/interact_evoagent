"""Workspace — enforce safe file access boundaries."""

from pathlib import Path


class Workspace:
    """A workspace is the root directory for all agent file operations.

    All paths are resolved relative to the workspace root, and
    paths that escape the workspace are rejected.
    """

    def __init__(self, root: str | Path = "."):
        """Initialize the workspace.

        Args:
            root: The workspace root directory path.
        """
        self.root = Path(root).resolve()
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path within the workspace.

        Args:
            path: Relative or absolute path.

        Returns:
            Resolved absolute path.

        Raises:
            PermissionError: If the resolved path escapes the workspace.
        """
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        resolved = p.resolve()
        self.assert_inside_workspace(resolved)
        return resolved

    def is_inside_workspace(self, path: str | Path) -> bool:
        """Check if a path is inside the workspace."""
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        try:
            resolved = p.resolve()
            resolved.relative_to(self.root)
            return True
        except (ValueError, OSError):
            return False

    def assert_inside_workspace(self, path: str | Path) -> None:
        """Raise PermissionError if the path escapes the workspace."""
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as err:
            raise PermissionError(
                f"Path '{path}' resolves to '{resolved}', "
                f"which is outside workspace '{self.root}'."
            ) from err

    def relative_path(self, path: str | Path) -> Path:
        """Return the path relative to the workspace root."""
        resolved = Path(path).resolve()
        self.assert_inside_workspace(resolved)
        return resolved.relative_to(self.root)

    # Directories to exclude from listings
    IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}

    def __repr__(self) -> str:
        return f"Workspace('{self.root}')"
