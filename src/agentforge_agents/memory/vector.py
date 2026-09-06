"""Vector store adapters - in-memory default plus a vector-store interface."""

from __future__ import annotations

import math
from typing import Any

from agentforge_agents.memory.base import VectorBackend
from agentforge_agents.schemas.memory import MemoryRecord, MemorySearchResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _norm(vector: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vector)) or 1.0


class InMemoryVectorStore(VectorBackend):
    """Single-process cosine-similarity vector store."""

    def __init__(self) -> None:
        self._vectors: dict[str, tuple[list[float], dict[str, Any]]] = {}

    async def upsert(self, record_id: str, vector: list[float], payload: dict) -> None:
        self._vectors[record_id] = (list(vector), dict(payload))

    async def search(
        self,
        vector: list[float],
        *,
        limit: int = 5,
        filter_payload: dict | None = None,
    ) -> list[tuple[float, dict]]:
        query_norm = _norm(vector)
        scored: list[tuple[float, dict]] = []
        for record_id, (stored, payload) in self._vectors.items():
            if filter_payload:
                if not all(payload.get(k) == v for k, v in filter_payload.items()):
                    continue
            similarity = _dot(vector, stored) / (query_norm * _norm(stored))
            scored.append((similarity, {"record_id": record_id, **payload}))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:limit]

    async def delete(self, record_id: str) -> bool:
        return self._vectors.pop(record_id, None) is not None

    async def clear(self) -> int:
        count = len(self._vectors)
        self._vectors.clear()
        return count

    async def close(self) -> None:
        self._vectors.clear()


class VectorMemory:
    """Long-term semantic memory: embeddings + a vector store.

    Records are embedded when ``embeddable=True``; plain keyword search is the
    fallback otherwise.
    """

    def __init__(self, store: VectorBackend | None = None, embedder: Any | None = None) -> None:
        from agentforge_agents.memory.embeddings import HashEmbeddingAdapter

        self.store = store or InMemoryVectorStore()
        self.embedder = embedder or HashEmbeddingAdapter()

    async def remember(self, record: MemoryRecord) -> MemoryRecord:
        """"""
        if not _embeddable(record) or not record.embedding:
            record.embedding = await self.embedder.embed(record.content)
        payload = record.model_dump(mode="json")
        await self.store.upsert(record.id, record.embedding or [], payload)
        return record

    async def recall(
        self, query: str, *, limit: int = 5, namespace: str | None = None
    ) -> list[MemorySearchResult]:
        query_vector = await self.embedder.embed(query)
        filters = {"namespace": namespace} if namespace else None
        hits = await self.store.search(query_vector, limit=limit, filter_payload=filters)
        results: list[MemorySearchResult] = []
        for score, payload in hits:
            plausible = min(1.0, max(0.0, float(score)))
            payload = dict(payload)
            payload.pop("record_id", None)
            record = MemoryRecord.model_validate(payload)
            results.append(MemorySearchResult(record=record, score=plausible))
        return results

    async def forget(self, record_id: str) -> bool:
        return await self.store.delete(record_id)

    async def clear(self) -> int:
        return await self.store.clear()

    async def close(self) -> None:
        await self.store.close()
        if hasattr(self.embedder, "close"):
            maybe = self.embedder.close()
            if hasattr(maybe, "__await__"):
                await maybe


def _embeddable(record: MemoryRecord) -> bool:
    return bool(record.metadata.get("embeddable", True))


__all__ = ["InMemoryVectorStore", "VectorMemory"]
