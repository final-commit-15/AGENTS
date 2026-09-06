"""Memory architecture - short-term, long-term, embeddings, routing, namespaces."""

from __future__ import annotations

from agentforge_agents.memory.base import MemoryBackend, VectorBackend
from agentforge_agents.memory.embeddings import (
    EmbeddingAdapter,
    EmbeddingFactory,
    HashEmbeddingAdapter,
    OllamaEmbeddingAdapter,
    OpenAIEmbeddingAdapter,
)
from agentforge_agents.memory.manager import MemoryManager
from agentforge_agents.memory.router import MemoryPolicies, MemoryRouter
from agentforge_agents.memory.short_term import InMemoryMemoryBackend, RedisMemoryBackend
from agentforge_agents.memory.vector import InMemoryVectorStore, VectorMemory

__all__ = [
    "EmbeddingAdapter",
    "EmbeddingFactory",
    "HashEmbeddingAdapter",
    "InMemoryMemoryBackend",
    "InMemoryVectorStore",
    "MemoryBackend",
    "MemoryManager",
    "MemoryPolicies",
    "MemoryRouter",
    "OllamaEmbeddingAdapter",
    "OpenAIEmbeddingAdapter",
    "RedisMemoryBackend",
    "VectorBackend",
    "VectorMemory",
]
