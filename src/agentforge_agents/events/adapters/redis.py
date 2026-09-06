"""Redis pub/sub event adapter for cross-process / cross-service events."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from agentforge_agents.events.adapters.base import EventAdapter
from agentforge_agents.schemas.events import ExecutionEvent
from agentforge_agents.utils.errors import AgentForgeError
from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.serialization import from_json, to_bytes

log = get_logger(__name__)
Handler = Callable[[ExecutionEvent], Awaitable[None]]


class RedisEventAdapter(EventAdapter):
    """Publishes events to Redis and relays remote events to local handlers.

    A background task consumes the ``agentforge.events`` channel and re-dispatches
    to local subscribers. Requires the ``redis`` package.
    """

    def __init__(
        self, url: str = "redis://localhost:6379/0", *, channel: str = "agentforge.events"
    ) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:  # pragma: no cover
            raise AgentForgeError("redis package not installed") from exc
        self._url = url
        self._channel = channel
        self._redis = aioredis.from_url(url, decode_responses=False)
        self._local: dict[str, dict[str, Handler]] = {}
        self._sub_id = 0
        self._task: asyncio.Task[Any] | None = None

    async def publish(self, event: ExecutionEvent, *, channel: str = "tasks") -> None:
        full_channel = f"{self._channel}.{channel}"
        await self._redis.publish(full_channel, to_bytes(event.model_dump(mode="json")))
        await self._dispatch_local(event, channel)

    def subscribe(self, handler: Handler, *, channel: str = "tasks") -> str:
        self._sub_id += 1
        sub_id = f"sub-{self._sub_id}"
        self._local.setdefault(channel, {})[sub_id] = handler
        return sub_id

    def unsubscribe(self, *, channel: str, sub_id: str) -> None:
        bucket = self._local.get(channel)
        if bucket:
            bucket.pop(sub_id, None)

    async def _dispatch_local(self, event: ExecutionEvent, channel: str) -> None:
        handlers = list(self._local.get(channel, {}).values())
        if handlers:
            await asyncio.gather(*(handler(event) for handler in handlers), return_exceptions=True)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._consume())

    async def _consume(self) -> None:  # pragma: no cover - daemon loop
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe(f"{self._channel}.*")
        try:
            async for message in pubsub.listen():
                if message.get("type") != "pmessage":
                    continue
                data = message.get("data")
                if not data:
                    continue
                try:
                    event = ExecutionEvent.model_validate(from_json(data))
                except Exception:  # noqa: BLE001
                    log.warning("events_invalid_payload_dropped")
                    continue
                channel = (message.get("channel") or b"").decode().rsplit(".", 1)[-1]
                await self._dispatch_local(event, channel)
        except asyncio.CancelledError:
            raise
        finally:
            await pubsub.aclose()

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._redis.aclose()


__all__ = ["RedisEventAdapter"]
