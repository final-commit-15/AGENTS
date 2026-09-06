"""Task state machine for deterministic orchestration transitions."""

from __future__ import annotations

from typing import Any

from agentforge_agents.utils.errors import OrchestrationError


class TaskStateMachine:
    """Audited transitions over the task lifecycle states.

    Valid transitions:

    * ``pending -> scheduled -> running``
    * ``running -> completed | failed | cancelled | timed_out``
    * ``failed -> retrying | cancelled`` (retry loop)
    * ``retrying -> running``
    * Any state -> ``failed`` (recovery hook)
    """

    _VALID: dict[str, frozenset[str]] = {
        "pending": frozenset({"scheduled", "cancelled", "failed"}),
        "scheduled": frozenset({"running", "cancelled", "failed"}),
        "running": frozenset({"completed", "failed", "cancelled", "timed_out"}),
        "retrying": frozenset({"running", "cancelled", "failed"}),
        "failed": frozenset({"retrying", "cancelled", "completed"}),
        "completed": frozenset(),
        "cancelled": frozenset(),
        "timed_out": frozenset({"retrying"}),
    }

    def __init__(self, initial: str = "pending") -> None:
        if initial not in self._VALID:
            raise OrchestrationError(f"invalid initial state: {initial!r}")
        self.state = initial
        self.history: list[dict[str, Any]] = []

    def transition(self, target: str, *, reason: str = "") -> str:
        """Move to ``target``, recording the transition in history."""
        if target not in self._VALID:
            raise OrchestrationError(f"unknown target state: {target!r}")
        if target not in self._VALID[self.state]:
            raise OrchestrationError(
                f"invalid transition {self.state!r} -> {target!r}",
                task_id=None,
            )
        self.history.append({"from": self.state, "to": target, "reason": reason})
        self.state = target
        return self.state

    def can(self, target: str) -> bool:
        return target in self._VALID.get(self.state, frozenset())

    def snapshot(self) -> dict[str, Any]:
        return {"state": self.state, "history": self.history}


__all__ = ["TaskStateMachine"]
