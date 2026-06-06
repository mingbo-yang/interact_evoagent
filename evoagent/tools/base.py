"""BaseTool — abstract base class for all tools."""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from evoagent.core.ids import generate_id
from evoagent.core.time import utc_now_iso
from evoagent.tools.schema import ToolResult


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BaseTool(ABC):
    """Abstract base class for all tools.

    Every tool must define:
    - name: unique identifier
    - description: human-readable purpose
    - input_schema: Pydantic model for argument validation
    - risk_level: low / medium / high
    - run(): async method returning ToolResult

    Optional:
    - output_schema: Pydantic model for output validation
    - permission_check: hook for PermissionPolicy (Phase 5)
    - event_callback: hook for EventLogger (Phase 3)
    """

    name: str = ""
    description: str = ""
    input_schema: type[BaseModel] = BaseModel
    output_schema: type[BaseModel] | None = None
    risk_level: RiskLevel = RiskLevel.LOW

    # Hooks for future integration (Phase 5 PermissionPolicy, Phase 3 EventLogger)
    permission_check: Callable[[str, dict[str, Any]], bool] | None = None
    event_callback: Callable[[str, dict[str, Any]], None] | None = None

    def validate_args(self, arguments: dict[str, Any]) -> BaseModel:
        """Validate and parse arguments against input_schema.

        Args:
            arguments: Raw argument dict.

        Returns:
            Validated Pydantic model instance.

        Raises:
            ValidationError: If arguments don't match the schema.
        """
        return self.input_schema.model_validate(arguments)

    def to_openai_tool_schema(self) -> dict[str, Any]:
        """Generate an OpenAI-compatible function-calling schema.

        Returns:
            Dict with type, function.name, function.description,
            and function.parameters (JSON Schema).
        """
        schema = self.input_schema.model_json_schema()
        # Remove JSON Schema keys that OpenAI doesn't need
        schema.pop("title", None)
        schema.pop("additionalProperties", None)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool.

        Args:
            **kwargs: Validated arguments matching input_schema.

        Returns:
            Standardized ToolResult.
        """
        ...

    async def arun(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate arguments and execute the tool.

        This is the main entry point called by ToolRegistry.
        Handles validation, timing, and error wrapping.

        Args:
            arguments: Raw argument dict.

        Returns:
            ToolResult with timing and error info.
        """
        started_at = utc_now_iso()
        t0 = time.monotonic()

        try:
            validated = self.validate_args(arguments)
            # Permission hook (future Phase 5)
            if self.permission_check:
                allowed = self.permission_check(self.name, validated.model_dump())
                if not allowed:
                    return ToolResult(
                        call_id=generate_id("call"),
                        name=self.name,
                        success=False,
                        error="Permission denied.",
                        started_at=started_at,
                        finished_at=utc_now_iso(),
                        duration_ms=int((time.monotonic() - t0) * 1000),
                    )
            result = await self.run(**validated.model_dump())
        except Exception as e:
            result = ToolResult(
                call_id=generate_id("call"),
                name=self.name,
                success=False,
                error=str(e),
                started_at=started_at,
                finished_at=utc_now_iso(),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        # Event hook (future Phase 3)
        if self.event_callback:
            self.event_callback(self.name, {"arguments": arguments, "success": result.success})

        # Ensure timing if not set by the tool itself
        if not result.started_at:
            result.started_at = started_at
        if not result.finished_at:
            result.finished_at = utc_now_iso()
        if not result.duration_ms:
            result.duration_ms = int((time.monotonic() - t0) * 1000)
        if not result.name:
            result.name = self.name

        return result


# ── Workspace utilities ───────────────────────────────────────────────


def resolve_workspace_path(
    path_str: str,
    workspace: Path,
    must_exist: bool = False,
) -> Path:
    """Resolve a path within the workspace, rejecting escape attempts.

    Args:
        path_str: User-provided path string.
        workspace: The workspace root directory.
        must_exist: If True, raise if the path doesn't exist.

    Returns:
        Resolved absolute path within workspace.

    Raises:
        PermissionError: If the path escapes the workspace.
        FileNotFoundError: If must_exist is True and the path doesn't exist.
    """
    p = Path(path_str)
    if not p.is_absolute():
        p = workspace / p
    resolved = p.resolve()

    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as err:
        raise PermissionError(
            f"Path escapes workspace: '{path_str}' resolves to '{resolved}' "
            f"which is outside workspace '{workspace}'."
        ) from err

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path not found: {resolved}")

    return resolved


# Default directories to hide in listings
_DEFAULT_HIDDEN_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache",
                        ".evoagent"}
