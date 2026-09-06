"""WebSocket event adapter used to push events to browsers and CLIs.

This adapter works with any websocket-compatible object exposing ``send_json``.
It is transport-agnostic so both FastAPI's ``WebSocket`` and raw
``websockets``/``starlette`` connections can be plugged in.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from agentforge_agents.events.adapters.base import EventAdapter
from agentforge_agents.schemas.events import ExecutionEvent
from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.serialization import to_json

log = get_logger(__name__)
Handler = Callable[[ExecutionEvent], Awaitable[None]]


class WebSocketLike(Protocol):
    """Minimal surface expected from a connected websocket."""

    async def send_text(self, data: str) -> None: ...
    async def close(self) -> None: ...


class WebSocketEventAdapter(EventAdapter):
    """Broadcasts serialized events to a set of connected websockets.

    Local handlers subscribed through :meth:`subscribe` also fire, enabling the
    same bus to serve HTTP polling and websocket streaming simultaneously.
    """

    def __init__(self) -> None:
        self._sockets: set[WebSocketLike] = set()
        self._local: dict[str, dict[str, Handler]] = {}
        self._sub_id = 0

    @property
    def connected(self) -> int:
        return len(self._sockets)

    def attach(self, socket: WebSocketLike) -> Callable[[], None]:
        """Register a connected socket; returns a detach callback."""
        self._sockets.add(socket)

        def detach() -> None:
            self._sockets.discard(socket)

        return detach

    async def publish(self, event: ExecutionEvent, *, channel: str = "tasks") -> None:
        payload = to_json(event.model_dump(mode="json"))
        stale: list[WebSocketLike] = []
        for socket in list(self._sockets):
            try:
                await socket.send_text(payload)
            except Exception:  # noqa: BLE001
                stale.append(socket)
        for socket in stale:
            self._sockets.discard(socket)
        await self._dispatch_local(event, channel)

    def subscribe(self, handler: Handler, *, channel: str = "tasks") -> str:
        self._sub_id += 1
        sub_id = f"ws-sub-{self._sub_id}"
        self._local.setdefault(channel, {})[sub_id] = handler
        return sub_id

    def unsubscribe(self, *, channel: str, sub_id: str) -> None:
        self._local.get(channel, {}).pop(sub_id, None)

    async def _dispatch_local(self, event: ExecutionEvent, channel: str) -> None:
        handlers = list(self._local.get(channel, {}).values())
        if handlers:
            await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)

    async def close(self) -> None:
        for socket in list(self._sockets):
            try:
                await socket.close()
            except Exception:  # noqa: BLE001
                pass
        self._sockets.clear()
        self._local.clear()


__all__ = ["WebSocketEventAdapter", "WebSocketLike"]
