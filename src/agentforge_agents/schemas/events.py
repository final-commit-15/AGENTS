"""Execution event schemas emitted on the event bus."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentforge_agents.utils.time import utc_now


class EventType(StrEnum):
    """All event types the framework and its agents may emit."""

    TASK_CREATED = "task.created"
    TASK_SCHEDULED = "task.scheduled"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_RETRYING = "task.retrying"
    TOOL_STARTED = "tool.started"
    TOOL_FINISHED = "tool.finished"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    MEMORY_WRITE = "memory.write"
    MEMORY_RETRIEVED = "memory.retrieved"
    MODEL_CALL = "model.call"
    ORCHESTRATOR_PLAN = "orchestrator.plan"
    WORKFLOW_STEP = "workflow.step"
    CUSTOM = "custom"


class ExecutionEvent(BaseModel):
    """A single timestamped event carried by the bus."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Unique event id.")
    type: EventType
    task_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    parent_id: str | None = Field(
        default=None, description="Correlating event id, e.g. a TOOL_STARTED parent."
    )
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: EventType,
        *,
        task_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        payload: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> ExecutionEvent:
        from agentforge_agents.utils.ids import new_id

        return cls(
            id=new_id("evt"),
            type=event_type,
            task_id=task_id,
            agent_id=agent_id,
            session_id=session_id,
            payload=payload or {},
            metadata=metadata,
        )


__all__ = ["EventType", "ExecutionEvent"]
