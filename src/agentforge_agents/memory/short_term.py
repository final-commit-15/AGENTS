"""Short-term memory backends - in-memory (default) and Redis."""

from __future__ import annotations

import json
from datetime import datetime

from agentforge_agents.memory.base import MemoryBackend
from agentforge_agents.schemas.memory import MemoryRecord, MemorySearchResult
from agentforge_agents.utils.errors import MemoryError
from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.time import utc_now

log = get_logger(__name__)


class InMemoryMemoryBackend(MemoryBackend):
    """Lock-light in-memory store. Per-instance isolation; use Redis for multi-process."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    @staticmethod
    def _key(record_id: str, namespace: str) -> str:
        return f"{namespace}:{record_id}"

    async def store(self, record: MemoryRecord) -> MemoryRecord:
        self._records[self._key(record.id, record.namespace)] = record
        return record

    async def get(
        self, record_id: str, *, namespace: str = "default", session_id: str | None = None
    ) -> MemoryRecord | None:
        record = self._records.get(self._key(record_id, namespace))
        if record is None or record.expired():
            return None
        return record

    async def search(
        self,
        query: str,
        *,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 5,
        kind: str | None = None,
    ) -> list[MemorySearchResult]:
        query = query.lower().strip()
        terms = [t for t in query.split() if t]
        now = utc_now()
        scored: list[MemorySearchResult] = []
        for record in self._records.values():
            if record.expired(now):
                continue
            if record.namespace != namespace:
                continue
            if (
                session_id is not None
                and record.session_id is not None
                and record.session_id != session_id
            ):
                # Session isolation: a record bound to another session is invisible.
                continue
            if kind is not None and record.kind != kind:
                continue
            content = record.content.lower()
            if terms and not all(term in content for term in terms):
                continue
            score = _keyword_score(query, content) if terms else 1.0
            scored.append(MemorySearchResult(record=record, score=score))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:limit]

    async def delete(self, record_id: str, *, namespace: str = "default") -> bool:
        return self._records.pop(self._key(record_id, namespace), None) is not None

    async def clear(self, *, namespace: str | None = None, session_id: str | None = None) -> int:
        removed = 0
        for key, record in list(self._records.items()):
            if namespace is not None and record.namespace != namespace:
                continue
            if session_id is not None and record.session_id != session_id:
                continue
            del self._records[key]
            removed += 1
        return removed

    async def prune_expired(self, *, now: datetime | None = None) -> int:
        now = now or utc_now()
        expired = [key for key, record in self._records.items() if record.expired(now)]
        for key in expired:
            del self._records[key]
        return len(expired)

    async def close(self) -> None:
        self._records.clear()


class RedisMemoryBackend(MemoryBackend):
    """Redis-backed short-term memory with TTL support, namespaces, and sessions.

    Records are JSON-serialized under ``agentforge:memory:{namespace}:{record_id}``
    with a per-record TTL and a secondary keyword index for basic retrieval.
    """

    TTL_NONE = 0

    def __init__(
        self, url: str = "redis://localhost:6379/0", *, prefix: str = "agentforge:memory"
    ) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:  # pragma: no cover
            raise MemoryError("redis package not installed") from exc
        self._redis = aioredis.from_url(url, decode_responses=False)
        self._prefix = prefix
        self._available = True

    def _key(self, namespace: str, record_id: str) -> str:
        return f"{self._prefix}:{namespace}:{record_id}"

    def _index_key(self, namespace: str) -> str:
        return f"{self._prefix}:{namespace}:index"

    async def store(self, record: MemoryRecord) -> MemoryRecord:
        key = self._key(record.namespace, record.id)
        payload = record.model_dump(mode="json")
        if record.expires_at is not None:
            ttl = max(1, int((record.expires_at - utc_now()).total_seconds()))
        elif record.metadata.get("ttl_seconds") or record.metadata.get("ttl"):
            ttl = int(record.metadata.get("ttl_seconds") or record.metadata.get("ttl"))
        else:
            ttl = self.TTL_NONE
        try:
            await self._redis.set(key, json.dumps(payload), ex=ttl if ttl else None)
            terms = set(_tokenize(record.content))
            if terms:
                trie: dict[str, list[str]] = {}
                for term in terms:
                    trie[f"{term}:{record.namespace}:{record.id}"] = [record.id, record.namespace]
                # Store keyword -> record ids for lightweight keyword search.
                pipe = self._redis.pipeline()
                for term in terms:
                    pipe.sadd(self._index_key(record.namespace), term)
                    pipe.sadd(f"{self._index_key(record.namespace)}:k:{term}", record.id)
                await pipe.execute()
        except Exception as exc:
            raise MemoryError(f"redis store failed: {exc}") from exc
        return record

    async def get(
        self, record_id: str, *, namespace: str = "default", session_id: str | None = None
    ) -> MemoryRecord | None:
        raw = await self._redis.get(self._key(namespace, record_id))
        if not raw:
            return None
        record = MemoryRecord.model_validate(json.loads(raw))
        return record if not record.expired() else None

    async def search(
        self,
        query: str,
        *,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 5,
        kind: str | None = None,
    ) -> list[MemorySearchResult]:
        terms = [t for t in _tokenize(query)]
        if not terms:
            return []
        candidate_ids: set[str] = set()
        for term in terms:
            member_ids = await self._redis.smembers(f"{self._index_key(namespace)}:k:{term}")
            candidate_ids.update(m.decode() for m in member_ids)
        scored: list[MemorySearchResult] = []
        for record_id in candidate_ids:
            record = await self.get(record_id, namespace=namespace)
            if record is None:
                continue
            if (
                session_id is not None
                and record.session_id is not None
                and record.session_id != session_id
            ):
                continue
            if kind is not None and record.kind != kind:
                continue
            scored.append(
                MemorySearchResult(
                    record=record, score=_keyword_score(query, record.content.lower())
                )
            )
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:limit]

    async def delete(self, record_id: str, *, namespace: str = "default") -> bool:
        deleted = await self._redis.delete(self._key(namespace, record_id))
        return bool(deleted)

    async def clear(self, *, namespace: str | None = None, session_id: str | None = None) -> int:
        pattern = f"{self._prefix}:{namespace if namespace else '*'}*"
        cursor = 0
        removed = 0
        scan = self._redis.scan_iter(match=pattern, count=500)
        async for key in scan:  # type: ignore[attr-defined]
            await self._redis.delete(key)
            removed += 1
        return removed

    async def close(self) -> None:
        self._available = False
        await self._redis.aclose()


def _tokenize(text: str) -> list[str]:
    return [t.lower().strip(".,!?;:()[]{}'\"") for t in text.split() if t.strip()]


def _keyword_score(query: str, content: str) -> float:
    terms = set(_tokenize(query))
    if not terms:
        return 1.0
    hits = sum(1 for term in terms if term in content)
    return hits / len(terms)


__all__ = ["InMemoryMemoryBackend", "RedisMemoryBackend"]
