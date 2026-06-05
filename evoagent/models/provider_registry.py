"""ProviderRegistry — manage LLM provider definitions and adapters."""

from typing import Any

from pydantic import BaseModel, Field


class ProviderDefinition(BaseModel):
    id: str = Field(..., description="Provider identifier: deepseek, openai, anthropic, etc.")
    display_name: str = Field(default="", description="Human-readable name.")
    adapter_type: str = Field(default="openai_compatible", description="Adapter class to use.")
    api_key_env: str | None = Field(default=None, description="Env var for API key.")
    base_url: str | None = Field(default=None, description="API base URL.")
    enabled: bool = Field(default=True, description="Whether this provider is enabled.")
    supports_model_discovery: bool = Field(default=False)
    discovery_ttl_seconds: int = Field(default=3600)
    metadata: dict[str, Any] = Field(default_factory=dict)


DEFAULT_PROVIDERS: list[ProviderDefinition] = [
    ProviderDefinition(id="deepseek", display_name="DeepSeek", adapter_type="deepseek",
                       api_key_env="DEEPSEEK_API_KEY", base_url="https://api.deepseek.com/v1",
                       supports_model_discovery=False),
    ProviderDefinition(id="openai", display_name="OpenAI", adapter_type="openai_compatible",
                       api_key_env="OPENAI_API_KEY", base_url="https://api.openai.com/v1",
                       supports_model_discovery=True),
    ProviderDefinition(id="anthropic", display_name="Anthropic", adapter_type="anthropic",
                       api_key_env="ANTHROPIC_API_KEY", base_url="https://api.anthropic.com/v1",
                       supports_model_discovery=False),
    ProviderDefinition(id="gemini", display_name="Google Gemini", adapter_type="gemini",
                       api_key_env="GEMINI_API_KEY",
                       base_url="https://generativelanguage.googleapis.com/v1beta",
                       supports_model_discovery=False),
    ProviderDefinition(id="mistral", display_name="Mistral AI", adapter_type="openai_compatible",
                       api_key_env="MISTRAL_API_KEY", base_url="https://api.mistral.ai/v1",
                       supports_model_discovery=True),
    ProviderDefinition(id="xai", display_name="xAI", adapter_type="openai_compatible",
                       api_key_env="XAI_API_KEY", base_url="https://api.x.ai/v1",
                       supports_model_discovery=False),
    ProviderDefinition(id="ollama", display_name="Ollama", adapter_type="ollama",
                       api_key_env=None, base_url="http://localhost:11434",
                       supports_model_discovery=True),
    ProviderDefinition(id="openai_compatible", display_name="OpenAI-Compatible",
                       adapter_type="openai_compatible", api_key_env=None, base_url=None,
                       supports_model_discovery=True),
]


class ProviderRegistry:
    """Central registry of LLM providers.

    Creates adapters lazily, checks API key availability.
    """

    def __init__(self):
        self._providers: dict[str, ProviderDefinition] = {}
        for p in DEFAULT_PROVIDERS:
            self._providers[p.id] = p

    def register(self, definition: ProviderDefinition) -> None:
        self._providers[definition.id] = definition

    def get(self, provider_id: str) -> ProviderDefinition | None:
        return self._providers.get(provider_id)

    def list_all(self) -> list[ProviderDefinition]:
        return sorted(self._providers.values(), key=lambda p: p.id)

    def list_enabled(self) -> list[ProviderDefinition]:
        return [p for p in self._providers.values() if p.enabled]

    def is_configured(self, provider_id: str) -> bool:
        import os
        p = self._providers.get(provider_id)
        if p is None:
            return False
        if p.api_key_env is None:
            return True  # Ollama etc. don't need keys
        return bool(os.getenv(p.api_key_env))

    def status_summary(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for p in self.list_all():
            if self.is_configured(p.id):
                result[p.id] = "authenticated"
            elif p.api_key_env is None:
                result[p.id] = "available"
            else:
                result[p.id] = "not configured"
        return result
