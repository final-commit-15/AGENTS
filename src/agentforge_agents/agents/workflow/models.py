"""I/O models for the Workflow Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkflowStepRequest(BaseModel):
    step_id: str = Field(min_length=1)
    input: dict = Field(default_factory=dict)


class WorkflowRunResult(BaseModel):
    run_id: str
    status: str
    steps: int = 0


__all__ = ["WorkflowRunResult", "WorkflowStepRequest"]
