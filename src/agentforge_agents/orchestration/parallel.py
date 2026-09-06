"""Parallel executor - runs independent plan tasks concurrently with a cap."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)
T = TypeVar("T")


class ParallelExecutor:
    """Fans out tasks with a concurrency limit and collects results by key."""

    def __init__(self, *, max_concurrency: int = 4) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.max_concurrency = max_concurrency

    async def run(
        self,
        items: list[Any],
        coro_factory: Callable[[Any], Awaitable[T]],
    ) -> dict[str, T]:
        """Execute one coroutine per item, preserving order in the result dict.

        ``coro_factory(item)`` returns the coroutine to schedule. Results are keyed
        by ``str(item)``; identical items share a key.
        """
        results: dict[str, T] = {}
        semaphore = asyncio.Semaphore(self.max_concurrency)
        pending: list[asyncio.Task[tuple[str, T]]] = []

        async def guarded(item: Any) -> tuple[str, T]:
            async with semaphore:
                value = await coro_factory(item)
                return str(item), value

        for item in items:
            pending.append(asyncio.create_task(guarded(item)))
        for task in pending:
            key, value = await task
            results[key] = value
        return results

    async def map(self, fn: Callable[[Any], Awaitable[T]], items: list[Any]) -> list[tuple[Any, T]]:
        """Convenience: run ``fn(item)`` for each item and pair with inputs."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def guarded(item: Any) -> tuple[Any, T]:
            async with semaphore:
                return item, await fn(item)

        return list(await asyncio.gather(*(guarded(item) for item in items)))

    async def run_plan(
        self,
        task_ids: list[str],
        coro_factory: Callable[[str], Awaitable[T]],
    ) -> dict[str, T]:
        """Execute plan task ids; duplicates are coalesced to one execution."""
        unique_ids = list(dict.fromkeys(task_ids))
        return await self.run(unique_ids, coro_factory)


__all__ = ["ParallelExecutor"]
