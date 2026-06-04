# Custom Models

## Using a Different OpenAI-Compatible API

```yaml
# evoagent.yaml
models:
  default:
    provider: openai_compatible
    model: your-model-name
    base_url: https://your-api.example.com/v1
    api_key_env: YOUR_API_KEY_ENV
```

Any API compatible with `/v1/chat/completions` works.

## Writing a Custom Provider

```python
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest, LLMResponse

class MyProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "my_provider"

    async def chat(self, request: LLMRequest) -> LLMResponse:
        # Your custom logic here
        return LLMResponse(content="Hello", model="my-model", provider="my_provider")

    async def structured_chat(self, request, schema):
        ...

    async def stream_chat(self, request):
        ...
```

Register in `ProviderFactory` or use directly with `ModelRouter`.

## Mock Provider for Testing

```python
from evoagent.models.factory import MockLLMProvider

mock = MockLLMProvider(
    fixed_text="Mock response",
    fixed_tool_calls=[ToolCall(name="read_file", arguments={"path": "test.txt"})],
    fixed_json={"key": "value"},
)
```

## Using LiteLLM (future)

LiteLLM provider is planned. For now, use `openai_compatible` with the LiteLLM proxy URL.
