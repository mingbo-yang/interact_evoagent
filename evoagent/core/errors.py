"""EvoAgent unified exception hierarchy."""


class EvoAgentError(Exception):
    """Base exception for all EvoAgent errors."""


class ConfigError(EvoAgentError):
    """Configuration loading or validation error."""


class ModelProviderError(EvoAgentError):
    """LLM provider error (API call failed, invalid response, etc.)."""


class ToolError(EvoAgentError):
    """Tool execution error."""


class PermissionDeniedError(EvoAgentError):
    """Permission policy denied an action."""


class SandboxError(EvoAgentError):
    """Sandbox execution error."""


class MemoryError(EvoAgentError):
    """Memory storage or retrieval error."""


class PlanningError(EvoAgentError):
    """Planning or task decomposition error."""


class EvaluationError(EvoAgentError):
    """Evaluation harness error."""
