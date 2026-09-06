"""In-memory asyncio event adapter (default for most deployments)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from agentforge_agents.events.adapters.base import EventAdapter
from agentforge_agents.schemas.events import ExecutionEvent

Handler = Callable[[ExecutionEvent], Awaitable[None]]


class LocalEventAdapter(EventAdapter):
    """Dispatches events to asyncio tasks per subscriber in the same process."""

    def __init__(self) -> None:
        self._subscribers: dict[str, dict[str, Handler]] = {}
        self._tasks: set[asyncio.Task[Any]] = set()

    async def publish(self, event: ExecutionEvent, *, channel: str = "tasks") -> None:
        handlers = list(self._subscribers.get(channel, {}).values())
        for handler in handlers:
            task = asyncio.create_task(handler(event))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def subscribe(self, handler: Handler, *, channel: str = "tasks") -> str:
        import uuid

        sub_id = uuid.uuid4().hex
        self._subscribers.setdefault(channel, {})[sub_id] = handler
        return sub_id

    def unsubscribe(self, *, channel: str, sub_id: str) -> None:
        bucket = self._subscribers.get(channel)
        if bucket:
            bucket.pop(sub_id, None)

    async def close(self) -> None:
        pending = [t for t in self._tasks if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._subscribers.clear()
        self._tasks.clear()


__all__ = ["LocalEventAdapter"]
