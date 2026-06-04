"""Sandbox and permission policy.

Provides:
- Workspace: safe file access boundaries
- PermissionPolicy: deny > ask > allow with review/auto/yolo modes
- BaseSandbox: abstract sandbox interface
- LocalSandbox: local execution with permission checks
- DockerSandbox: Docker-based sandbox (stub)
"""

from evoagent.sandbox.base import BaseSandbox  # noqa: F401
from evoagent.sandbox.docker import DockerSandbox  # noqa: F401
from evoagent.sandbox.local import LocalSandbox  # noqa: F401
from evoagent.sandbox.policy import PermissionPolicy  # noqa: F401
from evoagent.sandbox.schema import (  # noqa: F401
    PermissionDecision,
    PermissionMode,
    PermissionRule,
    PolicyConfig,
    SandboxResult,
)
from evoagent.sandbox.workspace import Workspace  # noqa: F401
