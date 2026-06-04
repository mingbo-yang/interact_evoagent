"""Tool system — registry, base classes, built-in tools.

Provides:
- BaseTool: abstract base class for all tools
- ToolRegistry: register, discover, and execute tools
- Built-in tools: read_file, write_file, edit_file, list_directory,
  grep, bash, python, git_status, git_diff
- ToolResult: standardized execution result (from schema.py)
"""

from evoagent.tools.base import BaseTool, RiskLevel, resolve_workspace_path  # noqa: F401
from evoagent.tools.builtin import create_builtin_registry  # noqa: F401
from evoagent.tools.file_tools import (  # noqa: F401
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from evoagent.tools.git_tools import GitDiffTool, GitStatusTool  # noqa: F401
from evoagent.tools.python_tools import PythonTool  # noqa: F401
from evoagent.tools.registry import ToolRegistry  # noqa: F401
from evoagent.tools.schema import ToolResult  # noqa: F401
from evoagent.tools.search_tools import GrepTool  # noqa: F401
from evoagent.tools.shell_tools import BashTool  # noqa: F401
