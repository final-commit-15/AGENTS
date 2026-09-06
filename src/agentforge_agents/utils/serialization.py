"""JSON serialization helpers built on orjson for speed and correct datetimes."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from enum import Enum
from typing import Any
from uuid import UUID

import orjson


def _default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_json(data: Any, *, pretty: bool = False, default: Any = _default) -> str:
    """Serialize ``data`` to a JSON string."""
    option = orjson.OPT_INDENT_2 if pretty else None
    return orjson.dumps(data, option=option, default=default).decode()


def to_bytes(data: Any, *, default: Any = _default) -> bytes:
    """Serialize ``data`` to JSON bytes (useful for Redis)."""
    return orjson.dumps(data, default=default)


def from_json(data: str | bytes) -> Any:
    """Parse JSON from string or bytes."""
    return orjson.loads(data)


def to_dict(obj: Any) -> dict[str, Any]:
    """Best-effort plain-dict conversion for Pydantic-style models."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return json.loads(to_json(obj))


def json_dumps(data: Any, *, default: Any = _default) -> str:
    """Pure-python fallback dump (handles ``**kwargs`` signatures)."""
    return json.dumps(data, default=default, ensure_ascii=False)


__all__ = ["from_json", "json_dumps", "to_bytes", "to_dict", "to_json"]
