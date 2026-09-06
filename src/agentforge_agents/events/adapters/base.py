"""Event adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from agentforge_agents.schemas.events import ExecutionEvent


class EventAdapter(ABC):
    """Transport contract for the event bus."""

    @abstractmethod
    async def publish(self, event: ExecutionEvent, *, channel: str = "tasks") -> None:
        """Send an event on the given channel."""

    @abstractmethod
    def subscribe(
        self, handler: Callable[[ExecutionEvent], Awaitable[None]], *, channel: str = "tasks"
    ) -> str:
        """Register a handler and return a subscription id."""

    @abstractmethod
    def unsubscribe(self, *, channel: str, sub_id: str) -> None:
        """Remove a previously created subscription."""

    async def start(self) -> None:  # noqa: B027
        pass

    async def close(self) -> None:  # noqa: B027
        pass


__all__ = ["EventAdapter"]
