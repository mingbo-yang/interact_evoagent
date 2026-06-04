"""Built-in tools — factory to create a ToolRegistry with all default tools."""

from pathlib import Path

from evoagent.tools.file_tools import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from evoagent.tools.git_tools import GitDiffTool, GitStatusTool
from evoagent.tools.python_tools import PythonTool
from evoagent.tools.registry import ToolRegistry
from evoagent.tools.search_tools import GrepTool
from evoagent.tools.shell_tools import BashTool


def create_builtin_registry(workspace: Path) -> ToolRegistry:
    """Create a ToolRegistry populated with all built-in tools.

    Args:
        workspace: The workspace root directory for file operations.

    Returns:
        ToolRegistry with read_file, write_file, edit_file,
        list_directory, grep, bash, python, git_status, git_diff.
    """
    registry = ToolRegistry(workspace=workspace)
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(EditFileTool(workspace))
    registry.register(ListDirTool(workspace))
    registry.register(GrepTool(workspace))
    registry.register(BashTool(workspace))
    registry.register(PythonTool(workspace))
    registry.register(GitStatusTool(workspace))
    registry.register(GitDiffTool(workspace))
    return registry
