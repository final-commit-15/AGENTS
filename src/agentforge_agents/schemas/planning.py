"""Planning schemas produced by the planner agent and consumed by the orchestrator."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PlanningStrategy(StrEnum):
    """How the planner chooses to decompose a request."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    MIXED = "mixed"


class PlanDependency(BaseModel):
    """A directed edge in the plan dependency graph."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="Dependency's task id.")
    target: str = Field(description="Task that depends on ``source``.")
    kind: str = Field(default="requires", description="requires | blocks | influences")


class PlanTask(BaseModel):
    """A single planned unit of work."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique task id within the plan.")
    agent_id: str = Field(description="Agent specialised to run this task.")
    instruction: str = Field(description="Concise instruction for the agent.")
    input: dict = Field(default_factory=dict, description="Structured task input.")
    priority: int = Field(default=0, ge=0)
    depends_on: list[str] = Field(
        default_factory=list, description="Plan task ids that must complete first."
    )
    parallel_group: str | None = Field(
        default=None, description="Tasks in the same group may run concurrently."
    )
    expected_output: str | None = Field(
        default=None, description="Description of the desired result."
    )
    metadata: dict = Field(default_factory=dict)


class PlannerResponse(BaseModel):
    """The full execution plan returned by a planner."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(description="Correlates with the original request id.")
    strategy: PlanningStrategy = PlanningStrategy.SEQUENTIAL
    goal: str = Field(description="Restated goal of the request.")
    tasks: list[PlanTask] = Field(default_factory=list)
    dependencies: list[PlanDependency] = Field(default_factory=list)
    rationale: str | None = Field(default=None, description="Why this decomposition was chosen.")
    total_estimated_tasks: int = 0

    def dependent_task_ids(self) -> dict[str, list[str]]:
        """Map task id -> list of plan task ids it depends on."""
        graph: dict[str, list[str]] = {t.id: [] for t in self.tasks}
        for dep in self.dependencies:
            if dep.target in graph and dep.source in graph:
                graph[dep.target].append(dep.source)
        for task in self.tasks:
            for source_id in task.depends_on:
                if source_id in graph:
                    graph[task.id].append(source_id)
        return graph

    def execution_order(self) -> list[list[str]]:
        """Topological layers (parallel batches) of task ids using Kahn's algorithm."""
        graph = self.dependent_task_ids()
        indegree = {tid: len(deps) for tid, deps in graph.items()}
        remaining = set(tid for tid, degree in indegree.items() if degree == 0)
        order: list[list[str]] = []
        total = len(graph)
        processed = 0
        while remaining:
            layer = sorted(remaining)
            order.append(layer)
            processed += len(layer)
            next_ready: set[str] = set()
            for tid in layer:
                for candidate, deps in graph.items():
                    if tid in deps:
                        indegree[candidate] -= 1
                        if indegree[candidate] == 0:
                            next_ready.add(candidate)
            remaining = next_ready
        if processed < total:
            leftover = [tid for tid, degree in indegree.items() if degree > 0]
            order.append(sorted(leftover))
        return order

    def has_cycles(self) -> bool:
        """True when the dependency graph contains a cycle (unexecutable plan)."""
        graph = {tid: list(deps) for tid, deps in self.dependent_task_ids().items()}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(tid: str) -> bool:
            if tid in visiting:
                return True
            if tid in visited:
                return False
            visiting.add(tid)
            for dep in graph[tid]:
                if visit(dep):
                    return True
            visiting.discard(tid)
            visited.add(tid)
            return False

        return any(visit(tid) for tid in graph)


__all__ = ["PlanDependency", "PlanTask", "PlannerResponse", "PlanningStrategy"]
