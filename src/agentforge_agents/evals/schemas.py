"""Structured evaluation records shared across the evals framework."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agentforge_agents.utils.time import utc_now


class EvalSample(BaseModel):
    """A single task bundled for evaluation with optional expected outcome."""

    id: str
    task: str
    expected: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class EvalOutcome(BaseModel):
    """Outcome of running one sample against an agent."""

    sample_id: str
    agent_id: str
    status: str = "completed"
    passed: bool = False
    score: float = 0.0
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    checked_at: datetime = Field(default_factory=utc_now)

    @property
    def ok(self) -> bool:
        return self.passed


class EvalReport(BaseModel):
    """Aggregate results for a single (dataset, agent) run."""

    dataset: str
    agent_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    accuracy: float = 0.0
    avg_duration_ms: float = 0.0
    outcomes: list[EvalOutcome] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class EvalConfig(BaseModel):
    """Configuration for a benchmark run."""

    datasets: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    max_samples: int = 100
    concurrency: int = 1
    timeout_seconds: float = 60.0
    report_path: str | None = None
    output_format: str = "json"


__all__ = ["EvalConfig", "EvalOutcome", "EvalReport", "EvalSample"]
