"""Timeout, cancellation, retry, streaming, and queue managers for execution."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from agentforge_agents.schemas.events import EventType, ExecutionEvent
from agentforge_agents.utils.errors import TaskCancelledError, TaskTimeoutError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)
T = TypeVar("T")


class TimeoutManager:
    """Decorator-free hard timeouts for async callables."""

    def __init__(self, default_seconds: float = 60.0) -> None:
        self.default_seconds = default_seconds

    async def run(self, fn: Callable[[], Awaitable[T]], *, seconds: float | None = None) -> T:
        budget = seconds or self.default_seconds
        try:
            return await asyncio.wait_for(fn(), timeout=budget)
        except TimeoutError as exc:
            raise TaskTimeoutError(f"execution exceeded {budget}s") from exc

    @staticmethod
    def deadline(seconds: float) -> float:
        return time.monotonic() + seconds

    @staticmethod
    def remaining(deadline: float) -> float:
        return max(0.0, deadline - time.monotonic())


@dataclass(slots=True)
class CancellationManager:
    """Cooperative task cancellation via asyncio events."""

    _events: dict[str, asyncio.Event] = field(default_factory=dict)

    def register(self, task_id: str) -> asyncio.Event:
        event = self._events.setdefault(task_id, asyncio.Event())
        event.clear()
        return event

    def request_cancel(self, task_id: str) -> bool:
        event = self._events.get(task_id)
        if event is None:
            return False
        event.set()
        log.info("cancellation_requested", task_id=task_id)
        return True

    def cancelled(self, task_id: str) -> bool:
        event = self._events.get(task_id)
        return bool(event and event.is_set())

    def check(self, task_id: str) -> None:
        if self.cancelled(task_id):
            raise TaskCancelledError(f"task {task_id!r} was cancelled")

    async def run(self, task_id: str, fn: Callable[[], Awaitable[T]]) -> T:
        if self.cancelled(task_id):
            raise TaskCancelledError(f"task {task_id!r} was cancelled before start")
        result = await fn()
        self.check(task_id)
        return result

    def release(self, task_id: str) -> None:
        self._events.pop(task_id, None)


@dataclass(slots=True)
class RetryManager:
    """Exponential-backoff retries over an async callable."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    retry_on: tuple[type[Exception], ...] = (Exception,)

    async def run(self, fn: Callable[[], Awaitable[T]], *, attempts: int | None = None) -> T:
        total = attempts or self.max_attempts
        for attempt in range(total):
            try:
                return await fn()
            except TaskCancelledError:
                raise
            except self.retry_on as exc:
                if attempt == total - 1:
                    raise
                delay = min(self.base_delay * (self.multiplier**attempt), self.max_delay)
                log.info("retry_scheduled", attempt=attempt + 1, delay=delay, error=str(exc))
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable")  # pragma: no cover


class StreamingManager:
    """Buffers and re-broadcasts async generators as typed events.

    Useful for translating a token stream into ``TASK_PROGRESS`` events without
    losing backpressure semantics.
    """

    def __init__(self, *, chunk_size: int = 256) -> None:
        self.chunk_size = chunk_size

    async def aggregate(self, stream: AsyncIterator[Any]) -> str:
        """Consume a token stream into a single string."""
        parts: list[str] = []
        async for chunk in stream:
            text = chunk if isinstance(chunk, str) else str(chunk)
            parts.append(text)
        return "".join(parts)

    async def to_progress_events(
        self,
        stream: AsyncIterator[Any],
        *,
        task_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """Wrap an async string stream into TASK_PROGRESS events (1..N chunks)."""
        index = 0
        async for chunk in stream:
            index += 1
            yield ExecutionEvent.create(
                EventType.TASK_PROGRESS,
                task_id=task_id,
                agent_id=agent_id,
                session_id=session_id,
                payload={"sequence": index, "delta": str(chunk)},
            )

    async def fan_out(
        self, stream: AsyncIterator[Any], consumers: list[Callable[[str], Awaitable[None]]]
    ) -> str:
        """Mirror a stream to multiple async consumers while aggregating."""
        parts: list[str] = []
        async for chunk in stream:
            text = chunk if isinstance(chunk, str) else str(chunk)
            parts.append(text)
            await asyncio.gather(
                *(consumer(text) for consumer in consumers), return_exceptions=True
            )
        return "".join(parts)


@dataclass(slots=True)
class QueueManager:
    """Bounded FIFO queue with typed payloads and worker dispatch."""

    capacity: int = 100
    _queue: deque[Any] = field(default_factory=deque)
    _condition: asyncio.Condition = field(default_factory=asyncio.Condition)

    async def put(self, item: Any) -> None:
        async with self._condition:
            while len(self._queue) >= self.capacity:
                await self._condition.wait()
            self._queue.append(item)
            self._condition.notify()

    async def get(self) -> Any:
        async with self._condition:
            while not self._queue:
                await self._condition.wait()
            item = self._queue.popleft()
            self._condition.notify()
            return item

    def size(self) -> int:
        return len(self._queue)

    async def process(self, handler: Callable[[Any], Awaitable[None]], *, workers: int = 1) -> None:
        """Run ``workers`` consumers; returns when the queue is drained."""

        async def worker() -> None:
            while True:
                try:
                    item = await asyncio.wait_for(self.get(), timeout=0.2)
                except TimeoutError:
                    if self.size() == 0:
                        return
                    continue
                await handler(item)

        await asyncio.gather(*(worker() for _ in range(workers)))


__all__ = [
    "CancellationManager",
    "QueueManager",
    "RetryManager",
    "StreamingManager",
    "TimeoutManager",
]
