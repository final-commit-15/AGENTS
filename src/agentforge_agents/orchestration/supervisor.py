"""Supervisor - watches plan execution and applies recovery policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentforge_agents.schemas.task import TaskResult, TaskStatus
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class SupervisorPolicy:
    """Recovery policy consulted by :class:`Supervisor`."""

    max_failures: int = 2
    retry_on_status: tuple[TaskStatus, ...] = (TaskStatus.FAILED, TaskStatus.TIMED_OUT)
    mark_prerequisites_failed: bool = True
    emit_reviews: bool = True


class Supervisor:
    """Reviews task results and recommends recovery actions.

    The supervisor never mutates orchestration state itself; it returns a
    ``SupervisorVerdict`` per task that the executor interprets.
    """

    def __init__(self, policy: SupervisorPolicy | None = None) -> None:
        self.policy = policy or SupervisorPolicy()
        self._failure_counts: dict[str, int] = {}
        self.reviews: list[dict[str, Any]] = []

    def review(self, task_id: str, result: TaskResult) -> dict[str, Any]:
        """Return a recovery verdict for ``result``."""
        if result.ok() and result.status != TaskStatus.PENDING:
            return {"task_id": task_id, "action": "none", "reason": "completed"}

        count = self._failure_counts.get(task_id, 0) + 1
        self._failure_counts[task_id] = count
        can_retry = (
            result.status in self.policy.retry_on_status and count <= self.policy.max_failures
        )
        action = "retry" if can_retry else "fail"
        reason = result.error or f"status {result.status.value}"
        if can_retry:
            reason = f"retry {count}/{self.policy.max_failures}: {reason}"
        verdict = {"task_id": task_id, "action": action, "reason": reason, "attempt": count}
        if self.policy.emit_reviews:
            self.reviews.append({"task_id": task_id, "action": action, "reason": reason})
            log.info("supervisor_review", **verdict)
        return verdict

    def review_all(self, results: dict[str, TaskResult]) -> dict[str, dict[str, Any]]:
        return {task_id: self.review(task_id, result) for task_id, result in results.items()}

    def reset(self, task_id: str | None = None) -> None:
        if task_id:
            self._failure_counts.pop(task_id, None)
        else:
            self._failure_counts.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "policy": {
                "max_failures": self.policy.max_failures,
                "retry_on_status": [s.value for s in self.policy.retry_on_status],
            },
            "failure_counts": dict(self._failure_counts),
            "reviews_count": len(self.reviews),
        }


__all__ = ["Supervisor", "SupervisorPolicy"]
