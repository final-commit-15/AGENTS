"""Identifier generation utilities."""

from __future__ import annotations

import secrets
import uuid


def uuid4_hex() -> str:
    """Cryptographically random hex id (32 chars)."""
    return uuid.uuid4().hex


def new_id(prefix: str = "id") -> str:
    """A readable prefixed id: ``{prefix}_{random-hex}``."""
    return f"{prefix}_{secrets.token_hex(8)}"


def task_id() -> str:
    """Short id suitable for tasks."""
    return uuid.uuid4().hex[:16]


def namespace_for(*parts: str | None) -> str:
    """Join non-empty namespace parts with ``:``, e.g. ``tenant:project:session``."""
    return ":".join(part for part in parts if part)


__all__ = ["namespace_for", "new_id", "task_id", "uuid4_hex"]
