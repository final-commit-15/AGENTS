"""Telemetry collection for latency, token usage, traces, and errors."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from agentforge_agents.utils.logging import get_logger
from agentforge_agents.utils.time import utc_now

log = get_logger(__name__)

try:  # pragma: no cover - optional metrics export
    from prometheus_client import REGISTRY as _PROM_DEFAULT_REGISTRY
    from prometheus_client import Counter, Gauge, Histogram

    _PROM_ENABLED = True
except ImportError:  # pragma: no cover
    _PROM_ENABLED = False
    _PROM_DEFAULT_REGISTRY = None  # type: ignore[assignment]

_PROM_METRICS: dict[str, Any] = {}

_PROM_METRICS: dict[str, Any] = {}


def _prom_metrics() -> dict[str, Any]:
    """Return a single process-wide set of prometheus metrics (created once)."""
    if not _PROM_ENABLED:
        return {}
    if _PROM_METRICS:
        return _PROM_METRICS
    _PROM_METRICS.update(
        {
            "latency": Histogram(
                "agentforge_latency_ms",
                "Agent operation latency in milliseconds",
                ["operation"],
            ),
            "tokens": Counter("agentforge_tokens_total", "Token usage", ["kind"]),
            "errors": Counter("agentforge_errors_total", "Agent errors"),
            "active": Gauge("agentforge_active_tasks", "Currently active tasks"),
        }
    )
    return _PROM_METRICS


class Telemetry:
    """In-process telemetry aggregator.

    Uses an asyncio-agnostic, lock-free design: each span appends to a bounded
    in-memory trace list. When ``prometheus_client`` is installed, a small set
    of process-wide metrics is exported as well.
    """

    def __init__(self, *, max_traces: int = 500) -> None:
        self._traces: list[dict[str, Any]] = []
        self.max_traces = max_traces
        self._counters: dict[str, int] = {}
        self.latency_total_ms = 0.0
        self.token_usage: dict[str, int] = {"prompt": 0, "completion": 0}
        self.errors = 0
        self._metrics = _prom_metrics()

    # -- recording -------------------------------------------------------------
    def record_trace(self, trace: dict[str, Any]) -> None:
        """Append a trace entry, trimming the oldest when over capacity."""
        if "timestamp" not in trace:
            trace["timestamp"] = utc_now().isoformat()
        self._traces.append(trace)
        if len(self._traces) > self.max_traces:
            del self._traces[: len(self._traces) - self.max_traces]

    def record_latency(self, operation: str, ms: float) -> None:
        self.latency_total_ms += ms
        if self._metrics:
            self._metrics["latency"].labels(operation).observe(ms)

    def record_tokens(self, prompt: int = 0, completion: int = 0) -> None:
        self.token_usage["prompt"] += prompt
        self.token_usage["completion"] += completion
        if self._metrics:
            self._metrics["tokens"].labels("prompt").inc(prompt)
            self._metrics["tokens"].labels("completion").inc(completion)

    def record_error(self, *, operation: str, error: str, task_id: str | None = None) -> None:
        self.errors += 1
        if self._metrics:
            self._metrics["errors"].inc()
        self.record_trace(
            {
                "operation": operation,
                "level": "error",
                "error": error,
                "task_id": task_id,
            }
        )
        if task_id:
            log.error("telemetry_error", operation=operation, task_id=task_id, error=error)

    def increment(self, key: str, amount: int = 1) -> None:
        self._counters[key] = self._counters.get(key, 0) + amount

    # -- spans -----------------------------------------------------------------
    @contextmanager
    def span(self, operation: str, **attrs: Any) -> Iterator[dict[str, Any]]:
        """Synchronous timing span recording latency and a structured trace."""
        started = time.monotonic()
        trace: dict[str, Any] = {"operation": operation, "status": "ok", **attrs}
        try:
            yield trace
        except Exception as exc:
            trace["status"] = "error"
            trace["error"] = str(exc)
            self.record_error(operation=operation, error=str(exc))
            raise
        finally:
            duration_ms = (time.monotonic() - started) * 1000.0
            trace["duration_ms"] = duration_ms
            self.record_latency(operation, duration_ms)
            self.record_trace(trace)

    @asynccontextmanager
    async def async_span(self, operation: str, **attrs: Any) -> AsyncIterator[dict[str, Any]]:
        """Async analogue of :meth:`span`."""
        started = time.monotonic()
        trace: dict[str, Any] = {"operation": operation, "status": "ok", **attrs}
        try:
            yield trace
        except Exception as exc:
            trace["status"] = "error"
            trace["error"] = str(exc)
            self.record_error(operation=operation, error=str(exc))
            raise
        finally:
            duration_ms = (time.monotonic() - started) * 1000.0
            trace["duration_ms"] = duration_ms
            self.record_latency(operation, duration_ms)
            self.record_trace(trace)

    def mark_task_started(self) -> None:
        if self._metrics:
            self._metrics["active"].inc()

    def mark_task_finished(self) -> None:
        if self._metrics:
            self._metrics["active"].dec()

    # -- snapshots --------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        """Immutable summary useful for reports and health endpoints."""
        return {
            "traces": list(self._traces),
            "counters": dict(self._counters),
            "latency_total_ms": self.latency_total_ms,
            "token_usage": dict(self.token_usage),
            "errors": self.errors,
        }

    def clear(self) -> None:
        self._traces.clear()
        self._counters.clear()
        self.latency_total_ms = 0.0
        self.token_usage = {"prompt": 0, "completion": 0}
        self.errors = 0


__all__ = ["Telemetry"]
