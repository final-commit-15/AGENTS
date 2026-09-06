"""Task lifecycle management - cancel, timeouts, retries, and state."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar

from agentforge_agents.schemas.task import TaskStatus
from agentforge_agents.utils.errors import RetryError, TaskCancelledError, TaskTimeoutError
from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.retry import RetryPolicy

log = get_logger(__name__)
T = TypeVar("T")


class LifecyclePhase(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(slots=True)
class TaskLifecycle:
    """Runtime bookkeeping for one in-flight task."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    cancel_requested: bool = False
    attempts: int = 0
    started_at: float | None = None
    finished_at: float | None = None
    retry_delay: float = field(default=0.0)

    @property
    def duration_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at or self.started_at
        return (end - self.started_at) * 1000.0


class LifecycleManager:
    """Coordinates cancellation, timeouts, and retries for tasks.

    The manager is intentionally single-eventloop: ``run`` wraps a raw async
    callable with a timeout and cooperative cancellation, reapplying retries
    according to the supplied :class:`RetryPolicy`.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskLifecycle] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------ registry
    def get(self, task_id: str) -> TaskLifecycle | None:
        return self._tasks.get(task_id)

    def register(self, task_id: str) -> TaskLifecycle:
        lifecycle = TaskLifecycle(task_id=task_id)
        self._tasks[task_id] = lifecycle
        self._cancel_events[task_id] = asyncio.Event()
        return lifecycle

    def release(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
        self._cancel_events.pop(task_id, None)

    # ----------------------------------------------------------- execution
    async def run(
        self,
        task_id: str,
        fn: Callable[[], Awaitable[T]],
        *,
        timeout_seconds: float | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> T:
        lifecycle = self.register(task_id)
        lifecycle.status = TaskStatus.SCHEDULED
        policy = retry_policy or RetryPolicy(max_attempts=1)
        for attempt in range(policy.max_attempts):
            lifecycle.attempts = attempt + 1
            lifecycle.status = TaskStatus.RUNNING
            lifecycle.started_at = _monotonic()
            try:
                result = await self._run_guarded(task_id, fn, timeout_seconds)
                lifecycle.status = TaskStatus.COMPLETED
                lifecycle.finished_at = _monotonic()
                self.release(task_id)
                return result
            except TaskCancelledError:
                lifecycle.status = TaskStatus.CANCELLED
                lifecycle.finished_at = _monotonic()
                self.release(task_id)
                raise
            except Exception as exc:
                lifecycle.finished_at = _monotonic()
                if attempt >= policy.max_attempts - 1:
                    lifecycle.status = TaskStatus.FAILED
                    self.release(task_id)
                    raise
                if not isinstance(exc, policy.retry_on):
                    lifecycle.status = TaskStatus.FAILED
                    self.release(task_id)
                    raise
                lifecycle.status = TaskStatus.RETRYING
                delay = policy.delay_for(attempt)
                log.info("task_retrying", task_id=task_id, attempt=attempt + 1, delay=delay)
                await asyncio.sleep(delay)
        raise RetryError("task retries exhausted")  # pragma: no cover

    async def _run_guarded(
        self, task_id: str, fn: Callable[[], Awaitable[T]], timeout_seconds: float | None
    ) -> T:
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event is None:
            cancel_event = asyncio.Event()
            self._cancel_events[task_id] = cancel_event
        cancel_event.clear()
        try:
            if timeout_seconds is not None and timeout_seconds > 0:
                return await asyncio.wait_for(fn(), timeout=timeout_seconds)
            return await fn()
        except TimeoutError as exc:
            raise TaskTimeoutError(f"task {task_id!r} exceeded {timeout_seconds}s budget") from exc
        finally:
            if cancel_event.is_set():
                raise TaskCancelledError(f"task {task_id!r} was cancelled")
            # NOTE: cancellation is cooperative; awaited functions should poll
            # ``self.is_cancelled(task_id)`` between long operations.

    # ---------------------------------------------------------- cancellation
    def request_cancel(self, task_id: str) -> bool:
        lifecycle = self._tasks.get(task_id)
        if lifecycle is None:
            return False
        lifecycle.cancel_requested = True
        event = self._cancel_events.get(task_id)
        if event is not None:
            event.set()
        return True

    def is_cancelled(self, task_id: str) -> bool:
        lifecycle = self._tasks.get(task_id)
        return lifecycle is not None and lifecycle.cancel_requested

    def cancel_notifier(self, task_id: str) -> asyncio.Event:
        return self._cancel_events.setdefault(task_id, asyncio.Event())

    def running_tasks(self) -> list[str]:
        return [
            tid
            for tid, lc in self._tasks.items()
            if lc.status in (TaskStatus.RUNNING, TaskStatus.SCHEDULED)
        ]

    def active_count(self) -> int:
        return len(self.running_tasks())


def _monotonic() -> float:
    import time

    return time.monotonic()


__all__ = ["LifecycleManager", "LifecyclePhase", "TaskLifecycle"]
