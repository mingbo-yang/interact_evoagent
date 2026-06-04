"""Checkers — evaluate whether agent output matches expected results."""

import json
import re

from evoagent.sandbox.base import BaseSandbox


class ExactMatchChecker:
    """Check if output exactly matches expected text."""
    @staticmethod
    def check(output: str, expected: str) -> bool:
        return output.strip() == expected.strip()


class ContainsChecker:
    """Check if output contains the expected substring."""
    @staticmethod
    def check(output: str, expected: str) -> bool:
        return expected in output


class RegexChecker:
    """Check if output matches a regex pattern."""
    @staticmethod
    def check(output: str, pattern: str) -> bool:
        try:
            return bool(re.search(pattern, output))
        except re.error:
            return False


class TestCommandChecker:
    """Run a shell command through Sandbox with PermissionPolicy.

    Never executes commands directly via subprocess.
    Requires a sandbox instance for all test_command checks.
    """

    def __init__(self, sandbox: BaseSandbox):
        self.sandbox = sandbox

    async def check(self, command: str, timeout: int = 30) -> bool:
        result = await self.sandbox.run_shell(command, timeout=timeout)
        return result.success


def evaluate_check(output: str, check_spec: str, workspace: str = ".",
                   sandbox: BaseSandbox | None = None) -> bool:
    """Evaluate an expected_check specification against agent output.

    check_spec format (JSON string):
        {"type": "contains", "value": "hello"}
        {"type": "exact", "value": "hello world"}
        {"type": "regex", "value": "pass(ed)?"}
        {"type": "test_command", "command": "pytest -q"}

    test_command checks require a sandbox. If no sandbox is provided,
    test_command checks return False with a security warning.

    Args:
        output: Agent's output text.
        check_spec: JSON string with type and value/command.
        workspace: Working directory (not used for test_command with sandbox).
        sandbox: Sandbox instance for test_command checks.

    Returns:
        True if the check passes.
    """
    try:
        spec = json.loads(check_spec)
    except json.JSONDecodeError:
        return False

    check_type = spec.get("type", "contains")
    value = spec.get("value", spec.get("command", ""))

    if check_type == "contains":
        return ContainsChecker.check(output, value)
    if check_type == "exact":
        return ExactMatchChecker.check(output, value)
    if check_type == "regex":
        return RegexChecker.check(output, value)
    if check_type == "test_command":
        if sandbox is None:
            return False  # Security: refuse to run without sandbox
        # Sync wrapper: create a fresh event loop to avoid
        # "cannot call asyncio.run() from running loop" errors.
        import asyncio
        checker = TestCommandChecker(sandbox)
        try:
            return asyncio.run(checker.check(value))
        except RuntimeError:
            # Fallback for already-running loops (rare in sync context)
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(checker.check(value), loop)
                return future.result(timeout=30)
            except RuntimeError:
                return False
        except Exception:
            return False
    return False


async def evaluate_check_async(output: str, check_spec: str, workspace: str = ".",
                               sandbox: BaseSandbox | None = None) -> bool:
    """Async version of evaluate_check."""
    try:
        spec = json.loads(check_spec)
    except json.JSONDecodeError:
        return False
    check_type = spec.get("type", "contains")
    value = spec.get("value", spec.get("command", ""))
    if check_type == "test_command":
        if sandbox is None:
            return False
        checker = TestCommandChecker(sandbox)
        return await checker.check(value)
    return evaluate_check(output, check_spec, workspace, sandbox=None)
