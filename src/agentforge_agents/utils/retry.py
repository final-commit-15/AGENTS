"""Async retry helpers with optional exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from agentforge_agents.utils.errors import RetryError

T = TypeVar("T")


@dataclass(slots=True)
class RetryPolicy:
    """Backoff configuration for retryable operations."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True
    retry_on: tuple[type[Exception], ...] = (Exception,)
    max_duration: float = 0.0  # 0 => unlimited wall-clock budget

    @property
    def attempts(self) -> int:
        return self.max_attempts

    def delay_for(self, attempt: int) -> float:
        """Backoff delay before retrying ``attempt`` (0-indexed)."""
        delay = min(self.base_delay * (self.multiplier**attempt), self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() / 2.0)
        return delay


@dataclass(slots=True)
class AsyncRetry:
    """An awaitable-driven retry wrapper around an async callable."""

    policy: RetryPolicy = field(default_factory=RetryPolicy)

    @staticmethod
    def _should_retry(exc: BaseException, policy: RetryPolicy) -> bool:
        return isinstance(exc, policy.retry_on)

    async def run(
        self,
        fn: Callable[[], Awaitable[T]],
        *,
        on_attempt: Callable[[int, BaseException | None], Awaitable[None] | None] | None = None,
    ) -> T:
        delay_elapsed = 0.0
        for attempt in range(self.policy.max_attempts):
            try:
                return await fn()
            except Exception as exc:
                if not self._should_retry(exc, self.policy):
                    raise
                if on_attempt is not None:
                    result = on_attempt(attempt, exc)
                    if result is not None:
                        await result
                if attempt == self.policy.max_attempts - 1:
                    raise RetryError(
                        f"operation failed after {self.policy.max_attempts} attempts: {exc}",
                        cause=exc,
                    ) from exc
                if self.policy.max_duration > 0 and delay_elapsed >= self.policy.max_duration:
                    raise RetryError("retry budget exhausted", cause=exc) from exc
                delay = self.policy.delay_for(attempt)
                delay_elapsed += delay
                await asyncio.sleep(delay)
        raise RetryError("unreachable")  # pragma: no cover


def retry(
    policy: RetryPolicy | None = None,
    *,
    max_attempts: int = 3,
    **policy_kwargs: Any,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator form of :class:`AsyncRetry`."""

    resolved = policy or RetryPolicy(max_attempts=max_attempts, **policy_kwargs)

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await AsyncRetry(resolved).run(lambda: fn(*args, **kwargs))

        return wrapper

    return decorator


__all__ = ["AsyncRetry", "RetryPolicy", "retry"]
