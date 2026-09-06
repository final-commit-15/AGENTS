"""Async token-bucket rate limiting with optional per-key isolation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from agentforge_agents.utils.errors import RateLimitError

T = TypeVar("T")


class RateLimiter:
    """A minimal token-bucket limiter.

    ``rate`` tokens are added per second, up to ``capacity``. Call
    :meth:`acquire` before a request; it blocks (optionally with a timeout)
    until a token is available.
    """

    def __init__(self, rate: float, capacity: float, *, default_key: str = "global") -> None:
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be positive")
        self._rate = rate
        self._capacity = capacity
        self._default_key = default_key
        self._tokens: dict[str, float] = {}
        self._updated: dict[str, float] = {}

    def _refill(self, key: str) -> float:
        now = time.monotonic()
        tokens = self._tokens.get(key, self._capacity)
        last = self._updated.get(key, now)
        tokens = min(self._capacity, tokens + (now - last) * self._rate)
        self._tokens[key] = tokens
        self._updated[key] = now
        return tokens

    def try_acquire(self, *, key: str | None = None) -> bool:
        """Non-blocking acquire; returns False when the bucket is empty."""
        k = key or self._default_key
        tokens = self._refill(k)
        if tokens >= 1.0:
            self._tokens[k] = tokens - 1.0
            return True
        return False

    async def acquire(self, *, key: str | None = None, timeout: float | None = None) -> None:
        """Blocking acquire honoring an optional per-call ``timeout``."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if self.try_acquire(key=key):
                return
            if deadline is not None and time.monotonic() >= deadline:
                raise RateLimitError("rate limit budget exhausted")
            await asyncio.sleep(self._poll_interval())

    def _poll_interval(self) -> float:
        # Sleep roughly long enough for one token to accrue, bounded.
        return max(0.001, min(1.0, 0.5 / self._rate))

    async def run(
        self,
        fn: Callable[[], Awaitable[T]],
        *,
        key: str | None = None,
        timeout: float | None = None,
    ) -> T:
        """Acquire a token then invoke an async zero-arg callable."""
        await self.acquire(key=key, timeout=timeout)
        return await fn()


__all__ = ["RateLimiter"]
