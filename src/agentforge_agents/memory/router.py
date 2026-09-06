"""Memory router - decides which backend a record targets and applies policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from agentforge_agents.memory.base import MemoryBackend
from agentforge_agents.memory.short_term import InMemoryMemoryBackend
from agentforge_agents.memory.vector import VectorMemory
from agentforge_agents.schemas.memory import MemoryRecord, MemorySearchResult
from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.time import utc_now

log = get_logger(__name__)


@dataclass(slots=True)
class MemoryPolicies:
    """Routing policy knobs applied by :class:`MemoryRouter`."""

    default_ttl_seconds: int = 86400
    session_isolation: bool = True
    short_term_kinds: tuple[str, ...] = ("conversation", "general")
    embeddable_kinds: tuple[str, ...] = ("user", "project", "task")
    max_short_results: int = 5
    max_long_results: int = 5
    enabled: bool = field(default=True)


class MemoryRouter:
    """Routes reads and writes to the appropriate memory layer.

    Short-term kinds (conversation, general) go to :class:`MemoryBackend`; long
    term kinds (user, project, task) additionally reach the semantic
    :class:`VectorMemory`. Reads merge semantic + keyword results when the
    query suggests long-term recall.
    """

    def __init__(
        self,
        short_term: MemoryBackend | None = None,
        long_term: VectorMemory | None = None,
        policies: MemoryPolicies | None = None,
    ) -> None:
        self.short_term = short_term or InMemoryMemoryBackend()
        self.long_term = long_term or VectorMemory()
        self.policies = policies or MemoryPolicies()

    # --------------------------------------------------------------- writes
    def _apply_policy(self, record: MemoryRecord) -> MemoryRecord:
        if record.expires_at is None and self.policies.default_ttl_seconds > 0:
            record.expires_at = utc_now() + timedelta(seconds=self.policies.default_ttl_seconds)
        if self.policies.session_isolation and record.session_id is None:
            record.session_id = "default"
        return record

    async def write(self, record: MemoryRecord) -> MemoryRecord:
        """Store a record, embedding long-term kinds automatically."""
        if not self.policies.enabled:
            return record
        self._apply_policy(record)
        record = await self.short_term.store(record)
        if record.kind in self.policies.embeddable_kinds:
            record = await self.long_term.remember(record)
        return record

    async def read(
        self, record_id: str, *, namespace: str = "default", session_id: str | None = None
    ) -> MemoryRecord | None:
        return await self.short_term.get(record_id, namespace=namespace, session_id=session_id)

    # --------------------------------------------------------------- reads
    async def search(
        self,
        query: str,
        *,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 5,
        kind: str | None = None,
    ) -> list[MemorySearchResult]:
        if not self.policies.enabled:
            return []
        short = await self.short_term.search(
            query, namespace=namespace, session_id=session_id, limit=limit, kind=kind
        )
        semantic: list[MemorySearchResult] = []
        if kind is None or kind in self.policies.embeddable_kinds:
            semantic = await self.long_term.recall(
                query, limit=self.policies.max_long_results, namespace=namespace
            )
        merged = _merge_unique(semantic, short)[:limit]
        return merged

    async def history(
        self,
        *,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """Most recent conversation history for a session (short-term scan)."""
        results = await self.short_term.search(
            "*", namespace=namespace, session_id=session_id, limit=limit, kind="conversation"
        )
        records = [hit.record for hit in results]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    async def forget(self, record_id: str, *, namespace: str = "default") -> bool:
        deleted = await self.short_term.delete(record_id, namespace=namespace)
        deleted = await self.long_term.forget(record_id) or deleted
        return deleted

    async def clear(self, *, namespace: str | None = None, session_id: str | None = None) -> int:
        removed = await self.short_term.clear(namespace=namespace, session_id=session_id)
        if namespace is None:
            removed += await self.long_term.clear()
        return removed

    async def close(self) -> None:
        await self.short_term.close()
        await self.long_term.close()


def _merge_unique(
    semantic: list[MemorySearchResult], keyword: list[MemorySearchResult]
) -> list[MemorySearchResult]:
    seen: set[str] = set()
    merged: list[MemorySearchResult] = []
    for hit in [*semantic, *keyword]:
        if hit.record.id in seen:
            continue
        seen.add(hit.record.id)
        merged.append(hit)
    return merged


__all__ = ["MemoryPolicies", "MemoryRouter"]
