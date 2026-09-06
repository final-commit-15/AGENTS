"""Embedding adapters - hash (local), OpenAI, and Ollama."""

from __future__ import annotations

import hashlib
import math
import struct
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import httpx

from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class EmbeddingAdapter(ABC):
    """Turns text into dense embedding vectors."""

    dimension: int

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single string."""

    async def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch (defaults to per-item calls)."""
        return [await self.embed(text) for text in texts]

    async def close(self) -> None:  # noqa: B027
        pass


class HashEmbeddingAdapter(EmbeddingAdapter):
    """Feature-hash embedding - deterministic, offline, zero dependencies.

    Suitable for development and tests. Produces a 256-dim pseudo-embedding by
    hashing character n-grams into a unit vector.
    """

    name = "hash"
    dimension = 256

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        lower = text.lower()
        ngrams: list[str] = []
        for size in (2, 3, 4):
            ngrams.extend(lower[i : i + size] for i in range(len(lower) - size + 1))
        if not ngrams:
            ngrams = [lower, " "]
        for token in ngrams:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            (index,) = struct.unpack("<I", digest[:4])
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index % self.dimension] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    """OpenAI embedding client (``text-embedding-3-small`` by default)."""

    name = "openai"

    def __init__(self, api_key: str | None, *, model: str = "text-embedding-3-small") -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package not installed") from exc
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        result = await self._client.embeddings.create(model=self.model, input=text)
        self.dimension = len(result.data[0].embedding)
        return result.data[0].embedding


class OllamaEmbeddingAdapter(EmbeddingAdapter):
    """Ollama embedding client over HTTP."""

    name = "ollama"

    def __init__(
        self, base_url: str = "http://localhost:11434", *, model: str = "nomic-embed-text"
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = 0

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            vector = response.json().get("embedding", [])
        self.dimension = len(vector)
        return vector


class EmbeddingFactory:
    """Constructs embedding adapters by provider name."""

    _registry: dict[str, type[EmbeddingAdapter]] = {
        HashEmbeddingAdapter.name: HashEmbeddingAdapter,
        OpenAIEmbeddingAdapter.name: OpenAIEmbeddingAdapter,
        OllamaEmbeddingAdapter.name: OllamaEmbeddingAdapter,
    }

    @classmethod
    def register(cls, name: str, adapter_type: type[EmbeddingAdapter]) -> None:
        cls._registry[name] = adapter_type

    @classmethod
    def create(cls, provider: str, **kwargs: Any) -> EmbeddingAdapter:
        adapter_type = cls._registry.get(provider)
        if adapter_type is None:
            raise ValueError(f"unknown embedding provider: {provider!r}")
        if provider == OpenAIEmbeddingAdapter.name:
            return adapter_type(
                kwargs.get("api_key"), model=kwargs.get("model", "text-embedding-3-small")
            )
        if provider == OllamaEmbeddingAdapter.name:
            return adapter_type(
                kwargs.get("base_url", "http://localhost:11434"), model=kwargs.get("model")
            )
        return adapter_type()


__all__ = [
    "EmbeddingAdapter",
    "EmbeddingFactory",
    "HashEmbeddingAdapter",
    "OllamaEmbeddingAdapter",
    "OpenAIEmbeddingAdapter",
]
