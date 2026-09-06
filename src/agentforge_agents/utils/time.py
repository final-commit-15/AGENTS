"""Date and time utilities."""

from __future__ import annotations

import time
from datetime import UTC, datetime


def now_utc() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def utc_now() -> datetime:
    """Alias of :func:`now_utc` (used as default factory across schemas)."""
    return now_utc()


def to_utc(value: datetime) -> datetime:
    """Ensure a datetime is timezone aware and expressed in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def now_iso() -> str:
    """Current UTC time in ISO-8601 format."""
    return now_utc().isoformat()


def epoch_ms(dt: datetime | None = None) -> int:
    """Millisecond epoch for a datetime (defaults to now)."""
    return int((dt or now_utc()).timestamp() * 1000)


def monotonic_ms() -> float:
    """Monotonic clock in milliseconds, safe for measuring durations."""
    return time.monotonic() * 1000.0


__all__ = ["epoch_ms", "monotonic_ms", "now_iso", "now_utc", "to_utc", "utc_now"]
