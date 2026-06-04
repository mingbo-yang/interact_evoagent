"""Code Agent module.

Provides:
- RepoMap: scan repository structure
- CodeSearch: text/symbol/file search
- PatchManager: generate and track patches
- CodeTestRunner: execute tests and capture results
- Diagnostics: parse test failures
- CodeAgent: the main code-fixing agent
"""

from evoagent.code.agent import CodeAgent, CodeAgentResult  # noqa: F401
from evoagent.code.diagnostics import Diagnostics  # noqa: F401
from evoagent.code.patch import PatchManager  # noqa: F401
from evoagent.code.repo_map import RepoMap  # noqa: F401
from evoagent.code.search import CodeSearch  # noqa: F401
from evoagent.code.test_runner import CodeTestRunner, TestResult  # noqa: F401
