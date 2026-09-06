"""Language-model client adapter layer.

Agents never talk to providers directly; they call :meth:`BaseLLMClient.chat`
/ :meth:`BaseLLMClient.stream`. Concrete adapters exist for OpenAI, Ollama and
a deterministic mock used by tests and evaluation suites.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from agentforge_agents.schemas.agent import ModelConfig
from agentforge_agents.schemas.common import Message
from agentforge_agents.utils.errors import LLMError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class ModelResponse:
    """Normalised chat completion result."""

    __slots__ = ("completion_tokens", "content", "meta", "model", "prompt_tokens")

    def __init__(
        self,
        content: str,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str = "",
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.model = model
        self.meta = meta or {}

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLLMClient(ABC):
    """Interface every provider adapter implements."""

    name: str = "base"

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    @abstractmethod
    async def chat(self, messages: Sequence[Message], **kwargs: Any) -> ModelResponse:
        """Complete a chat turn, returning the assistant's content."""

    async def stream(self, messages: Sequence[Message], **kwargs: Any) -> AsyncIterator[str]:
        """Yield content deltas as they arrive. Defaults to a single chunk."""
        response = await self.chat(messages, **kwargs)
        yield response.content

    async def close(self) -> None:  # noqa: B027 - optional hook
        pass


class OpenAILLMClient(BaseLLMClient):
    """OpenAI-compatible chat completion client (also covers Azure endpoints)."""

    name = "openai"

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise LLMError("openai package is not installed; add the 'llm' extra") from exc
        if not config.api_key and not config.base_url:
            log.warning("openai_client_without_api_key", model=config.name)
        self._client = AsyncOpenAI(
            api_key=config.api_key, base_url=config.base_url or None, timeout=config.timeout_seconds
        )

    async def chat(self, messages: Sequence[Message], **kwargs: Any) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.config.name),
            "messages": [m.to_openai() for m in messages],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        if kwargs.get("tools"):
            payload["tools"] = kwargs["tools"]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")
        try:
            result = await self._client.chat.completions.create(**payload)
        except Exception as exc:
            raise LLMError(f"openai call failed: {exc}", cause=exc) from exc
        first = result.choices[0].message if result.choices else None
        return ModelResponse(
            content=first.content or "" if first else "",
            prompt_tokens=getattr(result.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(result.usage, "completion_tokens", 0) or 0,
            model=result.model,
        )


class OllamaLLMClient(BaseLLMClient):
    """Ollama chat client driven over HTTP with httpx."""

    name = "ollama"

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        self._base_url = (config.base_url or "http://localhost:11434").rstrip("/")

    async def chat(self, messages: Sequence[Message], **kwargs: Any) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.config.name),
            "messages": [m.to_openai() for m in messages],
            "stream": False,
            "options": {"temperature": kwargs.get("temperature", self.config.temperature)},
        }
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"ollama call failed: {exc}", cause=exc) from exc
        return ModelResponse(
            content=data.get("message", {}).get("content", ""),
            prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
            completion_tokens=int(data.get("eval_count", 0) or 0),
            model=data.get("model", self.config.name),
        )

    async def stream(self, messages: Sequence[Message], **kwargs: Any) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.config.name),
            "messages": [m.to_openai() for m in messages],
            "stream": True,
            "options": {"temperature": kwargs.get("temperature", self.config.temperature)},
        }
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        import json

                        data = json.loads(line)
                        delta = data.get("message", {}).get("content", "")
                        if delta:
                            yield delta
        except httpx.HTTPError as exc:
            raise LLMError(f"ollama stream failed: {exc}", cause=exc) from exc


class MockLLMClient(BaseLLMClient):
    """Deterministic client for tests and offline evaluation.

    Echoes a canned ``mock_reply`` or a lower-cased summary of the last user
    message. Never performs network I/O.
    """

    name = "mock"

    def __init__(self, config: ModelConfig, *, reply: str | None = None) -> None:
        super().__init__(config)
        self.reply = reply

    async def chat(self, messages: Sequence[Message], **kwargs: Any) -> ModelResponse:
        reply = self.reply
        if reply is None:
            tail = [m.content for m in messages if m.role.value == "user"]
            reply = f"mock response to: {(tail[-1] if tail else '')[:120]}"
        return ModelResponse(
            content=reply, prompt_tokens=0, completion_tokens=len(reply) // 4, model="mock"
        )

    async def stream(self, messages: Sequence[Message], **kwargs: Any) -> AsyncIterator[str]:
        response = await self.chat(messages, **kwargs)
        for token in response.content.split(" "):
            yield token + " "


class LLMClientFactory:
    """Builds a client from a :class:`ModelConfig`."""

    _registry: dict[str, type[BaseLLMClient]] = {
        OpenAILLMClient.name: OpenAILLMClient,
        OllamaLLMClient.name: OllamaLLMClient,
        MockLLMClient.name: MockLLMClient,
    }

    @classmethod
    def register(cls, name: str, client_type: type[BaseLLMClient]) -> None:
        cls._registry[name] = client_type

    @classmethod
    def create(cls, config: ModelConfig) -> BaseLLMClient:
        client_type = cls._registry.get(config.provider)
        if client_type is None:
            raise LLMError(f"unknown model provider: {config.provider!r}")
        return client_type(config)


__all__ = [
    "BaseLLMClient",
    "LLMClientFactory",
    "MockLLMClient",
    "ModelResponse",
    "OllamaLLMClient",
    "OpenAILLMClient",
]
