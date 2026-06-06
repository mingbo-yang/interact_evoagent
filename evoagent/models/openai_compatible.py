"""OpenAICompatibleProvider — generic provider for any OpenAI-compatible API."""

import asyncio
import json
import os
import random
from collections.abc import AsyncIterator
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from pydantic import BaseModel

from evoagent.core.errors import ModelProviderError
from evoagent.core.message import ToolCall
from evoagent.core.redaction import redact_text as _redact
from evoagent.models.base import BaseLLMProvider
from evoagent.models.schema import LLMRequest, LLMResponse, ModelConfig

# Status codes that are worth retrying: rate limiting and transient server-side
# failures. Everything else (4xx other than 429) is a client error and is
# surfaced immediately.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Upper bound on how long we will wait between attempts, even if the server's
# Retry-After header asks for more. Prevents a single call from hanging the
# agent for minutes.
_MAX_BACKOFF_SECONDS = 120.0


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for any OpenAI-compatible chat completion API.

    Supports:
    - Chat completion with tools
    - JSON mode (via response_format)
    - Structured output parsing
    - Streaming (via async generator)
    - Automatic retry on transient errors
    """

    def __init__(self, config: ModelConfig):
        """Initialize with a ModelConfig.

        Args:
            config: Model configuration (provider, model, base_url, api_key_env, etc.).

        Raises:
            ModelProviderError: If the API key is not found in the environment.
        """
        self._config = config
        if not config.base_url:
            raise ModelProviderError(
                "Base URL is required for OpenAI-compatible providers. "
                "Set base_url in evoagent.yaml or use a provider with a default endpoint."
            )

        self._api_key = ""
        if config.api_key_env:
            self._api_key = os.getenv(config.api_key_env, "")
            if not self._api_key:
                raise ModelProviderError(
                    f"API key not found. Set the environment variable "
                    f"'{config.api_key_env}' or configure it in evoagent.yaml."
                )

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(config.timeout),
        )

    @property
    def provider_name(self) -> str:
        return self._config.provider

    # ── Public API ─────────────────────────────────────────────────

    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat completion request."""
        payload = self._build_payload(request, stream=False)
        raw = await self._send_request(payload)
        return self._parse_response(raw)

    async def structured_chat(
        self, request: LLMRequest, schema: type[BaseModel]
    ) -> BaseModel:
        """Send a request and parse the response into a Pydantic model.

        Forces JSON output mode and parses the result.
        """
        json_request = LLMRequest(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            response_format={"type": "json_object"},
            stream=False,
            metadata=request.metadata,
        )
        response = await self.chat(json_request)
        try:
            return schema.model_validate_json(response.content)
        except Exception as e:
            raise ModelProviderError(
                f"Failed to parse structured response into {schema.__name__}: {e}"
            ) from e

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream text chunks from a chat completion request.

        Text-only: this method yields assistant text deltas. Tool calls are
        NOT assembled from the stream — callers that pass tools must use
        ``chat()`` (non-streaming) to receive tool_calls reliably.
        """
        payload = self._build_payload(request, stream=True)

        if self._client.is_closed:
            raise ModelProviderError("HTTP client is closed.")

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise ModelProviderError(
                        f"HTTP {resp.status_code} from {self.provider_name}: {body.decode()[:500]}"
                    )
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as e:
            raise ModelProviderError(f"Stream request failed: {e}") from e

    # ── Internal ──────────────────────────────────────────────────

    def _build_payload(self, request: LLMRequest, stream: bool) -> dict[str, Any]:
        """Build the JSON payload for the API call."""
        msgs = []
        for m in request.messages:
            msg: dict[str, Any] = {"role": m.role.value, "content": m.content}
            if m.name:
                msg["name"] = m.name
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in m.tool_calls
                ]
            # Note: reasoning_content (DeepSeek thinking tokens) is intentionally
            # NOT sent back in the request. Per DeepSeek's reasoning-model API,
            # the chain-of-thought must be dropped from subsequent inputs; it is
            # retained on the internal Message for display only.
            msgs.append(msg)

        payload: dict[str, Any] = {
            "model": request.model or self._config.model,
            "messages": msgs,
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format
        return payload

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        """Parse a Retry-After header (seconds or HTTP-date) into seconds."""
        if not value:
            return None
        value = value.strip()
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
        try:
            from datetime import datetime
            retry_dt = parsedate_to_datetime(value)
            if retry_dt is not None:
                if retry_dt.tzinfo is None:
                    retry_dt = retry_dt.replace(tzinfo=UTC)
                delta = (retry_dt - datetime.now(UTC)).total_seconds()
                return max(0.0, delta)
        except (TypeError, ValueError, OverflowError):
            pass
        return None

    def _backoff_delay(self, attempt: int, retry_after: float | None) -> float:
        """Delay before the next attempt.

        Honors the server's ``Retry-After`` when present (capped), otherwise
        uses exponential backoff with full jitter.
        """
        if retry_after is not None:
            return min(retry_after, _MAX_BACKOFF_SECONDS)
        # Full jitter: random point in [0, base * 2**attempt], capped.
        ceiling = min(_MAX_BACKOFF_SECONDS, 1.0 * (2 ** attempt))
        return random.uniform(0.0, ceiling)

    async def _send_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST with retry on rate-limit (429), 5xx, and transient transport
        errors, respecting the server's ``Retry-After`` header.

        ``max_retries`` from the model config counts retries *after* the first
        attempt, so the total number of attempts is ``max_retries + 1``.
        """
        if self._client.is_closed:
            raise ModelProviderError("HTTP client is closed.")

        max_attempts = max(1, self._config.max_retries + 1)
        last_error: str = ""

        for attempt in range(max_attempts):
            retry_after: float | None = None
            try:
                response = await self._client.post("/chat/completions", json=payload)
            except httpx.TransportError as e:
                # Timeouts, connection drops, and protocol errors are transient.
                last_error = f"transport error: {e}"
            except httpx.HTTPError as e:
                # Other httpx errors (e.g. invalid URL) are not retryable.
                raise ModelProviderError(
                    f"Request to {self.provider_name} failed: {e}"
                ) from e
            else:
                if response.status_code in (401, 403):
                    raise ModelProviderError(
                        f"Authentication failed for {self.provider_name}. "
                        f"Check your {self._config.api_key_env} environment variable."
                    )
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in _RETRYABLE_STATUS:
                    # Non-retryable client error.
                    raise ModelProviderError(
                        f"HTTP {response.status_code} from {self.provider_name}: "
                        f"{_redact(response.text[:500])}"
                    )
                retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
                last_error = (
                    f"HTTP {response.status_code} from {self.provider_name}: "
                    f"{_redact(response.text[:500])}"
                )

            # Out of attempts — surface the last error.
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(self._backoff_delay(attempt, retry_after))

        raise ModelProviderError(
            f"Request to {self.provider_name} failed after {max_attempts} "
            f"attempt(s): {last_error}"
        )

    def _parse_response(self, raw: dict[str, Any]) -> LLMResponse:
        """Parse the raw API response into a standardized LLMResponse."""
        try:
            choice = raw.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content") or ""
            finish_reason = choice.get("finish_reason")

            # Parse tool calls
            tool_calls: list[ToolCall] | None = None
            raw_tool_calls = message.get("tool_calls")
            if raw_tool_calls:
                tool_calls = []
                for tc in raw_tool_calls:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(
                        ToolCall(
                            id=tc.get("id", ""),
                            name=func.get("name", ""),
                            arguments=args,
                            raw=func.get("arguments", "{}"),
                        )
                    )

            usage = raw.get("usage", {})

            # DeepSeek reasoning_content
            reasoning = message.get("reasoning_content") or raw.get("reasoning_content")

            return LLMResponse(
                content=content,
                model=raw.get("model", self._config.model),
                provider=self.provider_name,
                tool_calls=tool_calls,
                raw=raw,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                finish_reason=finish_reason,
                reasoning_content=reasoning,
            )
        except Exception as e:
            raise ModelProviderError(
                f"Failed to parse response from {self.provider_name}: {e}"
            ) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
