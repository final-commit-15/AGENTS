"""Workflow definition and run schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentforge_agents.utils.time import utc_now


class WorkflowStepType(StrEnum):
    """Kinds of steps a workflow definition may contain."""

    AGENT = "agent"
    TOOL = "tool"
    CONDITIONAL = "conditional"
    DELAY = "delay"
    PARALLEL = "parallel"
    SUBWORKFLOW = "subworkflow"


class WorkflowStep(BaseModel):
    """A single node inside a :class:`WorkflowDefinition`."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Step id unique within the workflow.")
    step_type: WorkflowStepType = WorkflowStepType.AGENT
    name: str = Field(default="step")
    agent_id: str | None = None
    tool_name: str | None = None
    input: dict = Field(
        default_factory=dict, description="Static input; ``$ref`` values are resolved from state."
    )
    output_key: str | None = Field(
        default=None, description="Where to store the step output in workflow state."
    )
    depends_on: list[str] = Field(default_factory=list)
    max_retries: int = Field(default=0, ge=0)
    timeout_seconds: float | None = Field(default=None)
    delay_seconds: float = Field(default=0.0, ge=0.0)
    on_success: str | None = Field(
        default=None, description="Next step id when this step succeeds."
    )
    on_failure: str | None = Field(
        default=None, description="Step to jump to when this step fails."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """A declarative, checkable, resumable workflow."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(default="")
    description: str = Field(default="")
    version: str = Field(default="1.0.0")
    steps: list[WorkflowStep] = Field(default_factory=list)
    entry_step: str | None = Field(default=None, description="Defaults to the first step.")
    timeout_seconds: float = Field(default=300.0, gt=0.0)
    max_retries: int = Field(default=1, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def step(self, step_id: str) -> WorkflowStep:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(f"no step named {step_id!r}")

    def entry(self) -> WorkflowStep:
        if self.entry_step:
            return self.step(self.entry_step)
        if not self.steps:
            raise ValueError(f"workflow {self.id!r} has no steps")
        return self.steps[0]

    def dependency_graph(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {s.id: [] for s in self.steps}
        for step in self.steps:
            for dep in step.depends_on:
                if dep in graph:
                    graph[step.id].append(dep)
        return graph


class StepResult(BaseModel):
    """Outcome of executing a single workflow step."""

    model_config = ConfigDict(extra="allow")

    step_id: str
    status: str = Field(default="completed")
    output: Any = None
    error: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    duration_ms: float = Field(default=0.0, ge=0.0)


class WorkflowRun(BaseModel):
    """A persisted execution of a :class:`WorkflowDefinition`."""

    model_config = ConfigDict(extra="allow")

    run_id: str
    workflow_id: str
    status: str = Field(default="pending")
    state: dict[str, Any] = Field(default_factory=dict, description="Maps output keys to values.")
    step_results: list[StepResult] = Field(default_factory=list)
    current_step: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def set_status(self, status: str) -> None:
        self.status = status
        self.updated_at = utc_now()


__all__ = [
    "StepResult",
    "WorkflowDefinition",
    "WorkflowRun",
    "WorkflowStep",
    "WorkflowStepType",
]
