"""Memory backend interface shared by short- and long-term stores."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from agentforge_agents.schemas.memory import MemoryRecord, MemorySearchResult


class MemoryBackend(ABC):
    """Contract for any concrete memory storage implementation."""

    @abstractmethod
    async def store(self, record: MemoryRecord) -> MemoryRecord:
        """Persist a record (upsert by record id)."""

    @abstractmethod
    async def get(
        self, record_id: str, *, namespace: str = "default", session_id: str | None = None
    ) -> MemoryRecord | None:
        """Fetch a single record."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 5,
        kind: str | None = None,
    ) -> list[MemorySearchResult]:
        """Keyword search over stored content."""

    @abstractmethod
    async def delete(self, record_id: str, *, namespace: str = "default") -> bool:
        """Remove a record; returns whether it existed."""

    @abstractmethod
    async def clear(self, *, namespace: str | None = None, session_id: str | None = None) -> int:
        """Delete records matching namespace/session filters; returns count."""

    async def prune_expired(self, *, now: datetime | None = None) -> int:
        """Remove expired records; optional hook defaulting to no-op."""
        return 0

    @abstractmethod
    async def close(self) -> None:
        """Release any held connections."""


class VectorBackend(ABC):
    """Contract for a dedicated vector store used by long-term memory."""

    @abstractmethod
    async def upsert(self, record_id: str, vector: list[float], payload: dict) -> None:
        """Insert or update an embedding with associated payload."""

    @abstractmethod
    async def search(
        self,
        vector: list[float],
        *,
        limit: int = 5,
        filter_payload: dict | None = None,
    ) -> list[tuple[float, dict]]:
        """Return ``(score, payload)`` pairs ordered by descending similarity."""

    @abstractmethod
    async def delete(self, record_id: str) -> bool:
        """Remove an embedding by id."""

    @abstractmethod
    async def clear(self) -> int:
        """Remove all embeddings; returns count removed."""

    @abstractmethod
    async def close(self) -> None:
        pass


__all__ = ["MemoryBackend", "VectorBackend"]
