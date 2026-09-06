"""In-process and remote event bus with pluggable adapters."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from agentforge_agents.events.adapters.base import EventAdapter
from agentforge_agents.events.adapters.local import LocalEventAdapter
from agentforge_agents.schemas.events import ExecutionEvent
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)

EventHandler = Callable[[ExecutionEvent], Awaitable[None] | None]


class Subscription:
    """Handle used to cancel an event subscription."""

    __slots__ = ("_adapter", "channel", "id")

    def __init__(self, sub_id: str, channel: str, adapter: EventAdapter) -> None:
        self.id = sub_id
        self.channel = channel
        self._adapter = adapter

    def unsubscribe(self) -> None:
        self._adapter.unsubscribe(channel=self.channel, sub_id=self.id)


class EventBus:
    """Publish/subscribe hub wrapping an :class:`EventAdapter`.

    Defaults to an in-process async adapter. When Redis is available the
    ``redis://`` transport can be selected via the ``AGENTFORGE_EVENT_BUS``
    environment variable. :meth:`publish` is a fire-and-forget broadcast;
    handlers run in dedicated tasks so publishing never blocks the caller.
    """

    def __init__(
        self, adapter: EventAdapter | None = None, *, default_channel: str = "tasks"
    ) -> None:
        self._adapter: EventAdapter | None = adapter
        self._local = adapter is None
        self.default_channel = default_channel
        self._started = False

    # ------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        if self._started:
            return
        self._ensure_local()
        self._started = True

    async def close(self) -> None:
        if self._adapter is not None:
            await self._adapter.close()
        self._started = False

    def _ensure_local(self) -> EventAdapter:
        if self._adapter is None:
            self._adapter = LocalEventAdapter()
        return self._adapter

    def backend_type(self) -> str:
        """Human-readable name of the active transport (local | redis | ...)."""
        adapter = self._adapter
        if adapter is None:
            return "local"
        name = getattr(adapter, "name", None)
        if name:
            return str(name)
        return type(adapter).__name__.replace("EventAdapter", "").lower()

    # ------------------------------------------------------------ publish
    async def publish(self, event: ExecutionEvent, *, channel: str | None = None) -> None:
        """Broadcast ``event`` on ``channel`` (default ``tasks``)."""
        if not self._started:
            await self.start()
        assert self._adapter is not None
        await self._adapter.publish(event, channel=channel or self.default_channel)

    # -------------------------------------------------------------- consume
    def subscribe(
        self,
        handler: EventHandler,
        *,
        channel: str | None = None,
        event_type: Any | None = None,
    ) -> Subscription:
        """Register ``handler`` for events; optionally filter by event type."""
        adapter = self._ensure_local()
        channel_name = channel or self.default_channel

        async def bounded(event: ExecutionEvent) -> None:
            if event_type is not None and event.type != event_type:
                return
            await handler(event)

        sub_id = adapter.subscribe(bounded, channel=channel_name)
        return Subscription(sub_id, channel_name, adapter)

    def subscribe_task(self, task_id: str, handler: EventHandler) -> Subscription:
        """Subscribe to events for a single task (correlated by ``task_id``)."""

        async def bounded(event: ExecutionEvent) -> None:
            if event.task_id == task_id:
                await handler(event)

        return self.subscribe(bounded)

    # ------------------------------------------------------------ plumbing
    def wait_for(
        self,
        *,
        event_type: Any = None,
        task_id: str | None = None,
        timeout: float = 5.0,
    ) -> Awaitable[ExecutionEvent]:
        """Create an awaitable that resolves when a matching event fires.

        Designed for tests and short-lived correlation waiters; the listener is
        removed automatically on timeout.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[ExecutionEvent] = loop.create_future()
        subscription: Subscription | None = None

        def matches(event: ExecutionEvent) -> bool:
            if event_type is not None and event.type != event_type:
                return False
            if task_id is not None and event.task_id != task_id:
                return False
            return True

        async def handler(event: ExecutionEvent) -> None:
            if matches(event) and not future.done():
                future.set_result(event)

        async def waiter() -> ExecutionEvent:
            nonlocal subscription
            subscription = self.subscribe(handler)
            try:
                return await asyncio.wait_for(future, timeout=timeout)
            except TimeoutError:
                raise TimeoutError(f"timed out waiting for event {event_type}") from None
            finally:
                if subscription is not None:
                    subscription.unsubscribe()

        return waiter()


__all__ = ["EventBus", "EventHandler", "Subscription"]
