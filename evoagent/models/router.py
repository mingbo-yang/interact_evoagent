"""ModelRouter — routes requests to the right provider based on role."""


from pydantic import BaseModel

from evoagent.core.errors import ModelProviderError
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest, LLMResponse, RouterConfig


class ModelRouter:
    """Routes LLM requests to different providers based on role.

    Roles:
    - planner: plans task decomposition
    - executor: executes individual steps
    - critic: evaluates and critiques results
    - summarizer: summarizes context
    - default: fallback for any unhandled role

    Each role can use a different model/provider. For example,
    planner/critic can use deepseek-reasoner while executor uses
    deepseek-chat for faster tool-calling.
    """

    def __init__(
        self,
        config: RouterConfig | None = None,
        providers: dict[str, BaseLLMProvider] | None = None,
    ):
        """Initialize the router.

        Args:
            config: RouterConfig mapping roles to ModelConfigs.
            providers: Pre-built provider instances keyed by role.
                If provided, config is ignored for provider selection.
        """
        self._config = config or RouterConfig()
        self._providers = providers or {}

    def register(self, role: str, provider: BaseLLMProvider) -> None:
        """Manually register a provider for a role."""
        self._providers[role] = provider

    def _get_provider(self, role: str) -> BaseLLMProvider:
        """Resolve a role to a provider instance."""
        if role in self._providers:
            return self._providers[role]
        if "default" in self._providers:
            return self._providers["default"]
        raise ModelProviderError(
            f"No provider registered for role '{role}' and no 'default' fallback."
        )

    async def chat(self, role: str, request: LLMRequest) -> LLMResponse:
        """Send a chat request using the provider for the given role.

        Args:
            role: One of planner/executor/critic/summarizer/default.
            request: The LLM request.

        Returns:
            LLMResponse from the selected provider.
        """
        provider = self._get_provider(role)
        return await provider.chat(request)

    async def structured_chat(
        self, role: str, request: LLMRequest, schema: type[BaseModel]
    ) -> BaseModel:
        """Send a request and parse into a Pydantic model.

        Args:
            role: The role selecting the provider.
            request: The LLM request.
            schema: Pydantic model to parse into.

        Returns:
            Instance of the schema.
        """
        provider = self._get_provider(role)
        return await provider.structured_chat(request, schema)
