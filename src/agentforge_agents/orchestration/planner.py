"""Task planner - decomposes requests into dependency-aware execution plans."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentforge_agents.schemas.planning import (
    PlanDependency,
    PlannerResponse,
    PlanningStrategy,
    PlanTask,
)

RoutingCallable = Callable[[dict[str, Any], str | None], str]


class _StaticRouter:
    """Routes every task to a fixed agent or by an explicit input target."""

    def __init__(self, agent_id: str | None = None) -> None:
        self.agent_id = agent_id

    def __call__(self, input_data: dict[str, Any], instruction: str | None = None) -> str:
        return input_data.get("agent_id") or self.agent_id or "planner"


class TaskPlanner:
    """Builds a :class:`PlannerResponse` from a request description.

    ``router`` maps (input, instruction) -> agent id and determines where each
    subtask runs. The default heuristic splits multi-sentence requests into
    logical subtasks; providers (LLM-driven planners) can replace it wholesale.
    """

    def __init__(self, route: RoutingCallable | None = None, *, max_tasks: int = 10) -> None:
        self.route = route or _StaticRouter()
        self.max_tasks = max_tasks

    async def plan(
        self,
        *,
        request_id: str,
        goal: str,
        input_data: dict[str, Any] | None = None,
        agent_hints: list[str] | None = None,
        strategy: PlanningStrategy = PlanningStrategy.SEQUENTIAL,
    ) -> PlannerResponse:
        """Produce a plan for ``goal``. With no hints, a single-task plan is made."""
        input_data = input_data or {}
        agent_ids = [hint for hint in (agent_hints or []) if hint]
        if not agent_ids:
            preferred = input_data.get("agent_id") or self.route(input_data, goal)
            return self._single(request_id, goal, input_data, preferred, strategy)

        tasks = [
            PlanTask(
                id=f"t{i + 1}",
                agent_id=agent_id,
                instruction=(
                    goal if i == 0 else f"Complete the {agent_id} portion of the goal: {goal}"
                ),
                input=dict(input_data),
                priority=len(agent_ids) - i,
            )
            for i, agent_id in enumerate(agent_ids)
        ]

        plan = PlannerResponse(
            request_id=request_id,
            strategy=strategy,
            goal=goal,
            tasks=tasks,
            rationale="Sequenced the requested agent hints in dependency order.",
            total_estimated_tasks=len(tasks),
        )
        # Sequential plans chain tasks; parallel plans run everything together.
        if strategy == PlanningStrategy.PARALLEL:
            for index, task in enumerate(tasks):
                task.parallel_group = "root"
                task.depends_on = []
            plan.dependencies = [
                PlanDependency(source="root", target=task.id, kind="influences") for task in tasks
            ]
        else:
            for index in range(1, len(tasks)):
                tasks[index].depends_on = [tasks[index - 1].id]
                plan.dependencies.append(
                    PlanDependency(
                        source=tasks[index - 1].id, target=tasks[index].id, kind="requires"
                    )
                )
        plan.total_estimated_tasks = len(tasks)
        return plan

    def _single(
        self,
        request_id: str,
        goal: str,
        input_data: dict[str, Any],
        agent_id: str,
        strategy: PlanningStrategy,
    ) -> PlannerResponse:
        return PlannerResponse(
            request_id=request_id,
            strategy=strategy,
            goal=goal,
            tasks=[
                PlanTask(
                    id="t1",
                    agent_id=agent_id,
                    instruction=goal,
                    input=dict(input_data),
                    priority=0,
                )
            ],
            rationale="Single-task decomposition chosen for this request.",
            total_estimated_tasks=1,
        )


__all__ = ["TaskPlanner"]
