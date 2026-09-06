"""MemoryManager - the facade agents and workflows use for persistence.

Connects the router to the event bus so memory writes are observable, and
provides the ``remember`` / ``retrieve`` API used throughout the framework.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentforge_agents.memory.router import MemoryPolicies, MemoryRouter
from agentforge_agents.schemas.events import EventType, ExecutionEvent
from agentforge_agents.schemas.memory import MemoryRecord, MemorySearchResult
from agentforge_agents.utils.ids import new_id
from agentforge_agents.utils.logging import get_logger

if TYPE_CHECKING:
    from agentforge_agents.events.bus import EventBus

log = get_logger(__name__)


class MemoryManager:
    """High-level memory API bound to a router and optional event bus."""

    def __init__(
        self,
        router: MemoryRouter | None = None,
        *,
        events: EventBus | None = None,
        session_id: str | None = None,
        namespace: str | None = None,
    ) -> None:
        self.router = router or MemoryRouter()
        self.events = events
        self.session_id = session_id
        self.namespace = namespace
        self._embedder_provider: str | None = None

    # ------------------------------------------------------------- control
    def configure(
        self,
        *,
        session_id: str | None = None,
        namespace: str | None = None,
        policies: MemoryPolicies | None = None,
    ) -> None:
        if session_id is not None:
            self.session_id = session_id
        if namespace is not None:
            self.namespace = namespace
        if policies is not None:
            self.router.policies = policies

    # ------------------------------------------------------------- writes
    async def remember(
        self,
        record: MemoryRecord,
        *,
        session_id: str | None = None,
        namespace: str | None = None,
    ) -> MemoryRecord:
        """Persist a memory record under the manager's (or explicit) context."""
        if record.namespace == "default":
            record.namespace = namespace or self.namespace or record.namespace
        if record.session_id is None:
            record.session_id = session_id or self.session_id
        if record.id in {"", "placeholder"}:
            record.id = new_id("mem")
        stored = await self.router.write(record)
        if self.events is not None:
            await self.events.publish(
                ExecutionEvent.create(
                    EventType.MEMORY_WRITE,
                    session_id=stored.session_id,
                    payload={
                        "record_id": stored.id,
                        "kind": stored.kind,
                        "namespace": stored.namespace,
                    },
                )
            )
        log.debug("memory_remembered", record_id=stored.id, kind=stored.kind)
        return stored

    async def remember_text(
        self,
        content: str,
        *,
        kind: str = "general",
        namespace: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        embeddable: bool | None = None,
    ) -> MemoryRecord:
        """Convenience wrapper creating a record from plain text."""
        record = MemoryRecord(
            id=new_id("mem"),
            namespace=namespace or self.namespace or "default",
            session_id=session_id or self.session_id,
            kind=kind,
            content=content,
            metadata={
                **(metadata or {}),
                "embeddable": (
                    embeddable
                    if embeddable is not None
                    else kind in self.router.policies.embeddable_kinds
                ),
            },
        )
        return await self.remember(record)

    # ------------------------------------------------------------- reads
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        namespace: str | None = None,
        session_id: str | None = None,
        kind: str | None = None,
    ) -> list[MemorySearchResult]:
        """Semantic + keyword search across memory, merging both layers."""
        results = await self.router.search(
            query,
            namespace=namespace or self.namespace or "default",
            session_id=session_id or self.session_id,
            limit=limit,
            kind=kind,
        )
        if self.events is not None:
            await self.events.publish(
                ExecutionEvent.create(
                    EventType.MEMORY_RETRIEVED,
                    session_id=session_id or self.session_id,
                    payload={"query": query, "hits": [r.record.id for r in results]},
                )
            )
        return results

    async def retrieve_text(self, query: str, *, limit: int = 5, **kwargs: Any) -> list[str]:
        """Convenience wrapper returning only record contents."""
        hits = await self.retrieve(query, limit=limit, **kwargs)
        return [hit.record.content for hit in hits]

    async def history(
        self, *, session_id: str | None = None, limit: int = 50
    ) -> list[MemoryRecord]:
        return await self.router.history(
            namespace=self.namespace or "default",
            session_id=session_id or self.session_id,
            limit=limit,
        )

    async def forget(self, record_id: str, *, namespace: str | None = None) -> bool:
        return await self.router.forget(
            record_id, namespace=namespace or self.namespace or "default"
        )

    async def clear(self, *, namespace: str | None = None, session_id: str | None = None) -> int:
        return await self.router.clear(namespace=namespace, session_id=session_id)

    async def close(self) -> None:
        await self.router.close()


__all__ = ["MemoryManager"]
