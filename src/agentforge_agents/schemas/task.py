"""Task request/result schemas exchanged with the backend and between agents."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

import orjson
from pydantic import BaseModel, ConfigDict, Field

from agentforge_agents.utils.time import utc_now


class TaskStatus(StrEnum):
    """Lifecycle states of a task through the execution engine."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    RETRYING = "retrying"


class ToolCall(BaseModel):
    """A recorded invocation of a tool by an agent or workflow."""

    model_config = ConfigDict(extra="allow")

    call_id: str = Field(description="Unique call identifier.")
    tool_name: str = Field(description="Registered name of the tool.")
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="started")
    output: Any = None
    error: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    duration_ms: float = Field(default=0.0, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    """A self-contained task submitted to an agent or the orchestrator."""

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(description="Unique task identifier.")
    agent_id: str | None = Field(
        default=None, description="Target agent; None routes automatically."
    )
    input: dict[str, Any] = Field(default_factory=dict, description="Free-form task input.")
    instructions: str | None = Field(
        default=None, description="Optional free-form user instruction."
    )
    parent_task_id: str | None = None
    context: dict[str, Any] = Field(
        default_factory=dict, description="Shared runtime context (session, etc.)."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, description="Higher is more urgent.")
    timeout_seconds: float | None = Field(default=None, description="Per-task timeout override.")
    max_retries: int | None = Field(default=None, description="Per-task retry override.")
    created_at: datetime = Field(default_factory=utc_now)

    def text_input(self) -> str:
        """Stable string form of the input suitable for templating and search."""
        return orjson.dumps(self.input, default=str).decode()


class TaskResult(BaseModel):
    """Outcome of executing a task."""

    model_config = ConfigDict(extra="allow")

    task_id: str
    agent_id: str | None = None
    status: TaskStatus = TaskStatus.COMPLETED
    output: Any = None
    error: str | None = None
    trace: list[str] = Field(default_factory=list, description="Ordered execution trace steps.")
    tool_calls: list[ToolCall] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    duration_ms: float = Field(default=0.0, ge=0.0)
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Tokens, latency, cost, ..."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def ok(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.PENDING)

    @classmethod
    def success(cls, task_id: str, output: Any, agent_id: str | None = None) -> TaskResult:
        return cls(task_id=task_id, agent_id=agent_id, status=TaskStatus.COMPLETED, output=output)

    @classmethod
    def failure(cls, task_id: str, error: str, agent_id: str | None = None) -> TaskResult:
        return cls(task_id=task_id, agent_id=agent_id, status=TaskStatus.FAILED, error=error)


__all__ = ["TaskRequest", "TaskResult", "TaskStatus", "ToolCall"]
