"""Execution primitives shared by sandbox, docker runner, and queue workers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RunResult:
    """Normalised outcome of an execution."""

    success: bool = True
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any, **metadata: Any) -> RunResult:
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def err(cls, error: str, **metadata: Any) -> RunResult:
        return cls(success=False, error=error, metadata=metadata)


class ExecutionTarget(ABC):
    """Anything the engine can execute against."""

    @abstractmethod
    async def run_code(
        self,
        code: str | list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        interpreter: str | None = None,
    ) -> dict[str, Any]:
        """Run code or a command line, returning a raw result dict."""


__all__ = ["ExecutionTarget", "RunResult"]
