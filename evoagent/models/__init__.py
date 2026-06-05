"""Model Provider abstraction layer.

Provides:
- BaseLLMProvider: abstract interface
- OpenAICompatibleProvider: generic OpenAI-compatible adapter
- DeepSeekProvider: DeepSeek-specific provider
- ModelRouter: role-based provider routing
- ProviderFactory: create providers from config
- MockLLMProvider: mock for testing
"""

from evoagent.models.base import BaseLLMProvider  # noqa: F401
from evoagent.models.deepseek import DeepSeekProvider  # noqa: F401
from evoagent.models.factory import MockLLMProvider, ProviderFactory  # noqa: F401
from evoagent.models.openai_compatible import OpenAICompatibleProvider  # noqa: F401
from evoagent.models.provider_registry import ProviderRegistry  # noqa: F401
from evoagent.models.registry import ModelDefinition, ModelRegistry  # noqa: F401
from evoagent.models.router import ModelRouter  # noqa: F401
from evoagent.models.schema import (  # noqa: F401
    LLMRequest,
    LLMResponse,
    ModelConfig,
    RouterConfig,
)
