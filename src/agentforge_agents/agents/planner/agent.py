"""Planner Agent - decomposes requests into execution plans."""

from __future__ import annotations

from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Analyzes requests and produces dependency-aware, parallelizable plans.

    ``execute`` returns a structured plan as ``TaskResult.output`` while
    ``plan`` returns the raw :class:`PlannerResponse` consumed by the
    orchestrator.
    """

    @property
    def default_tools(self) -> list[str]:
        return ["search", "http"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        """Produce a plan for the request (heuristic or LLM-assisted)."""
        goal = request.instructions or request.text_input()
        hint = request.input.get("agent_id") if request.input else None
        if hint:
            return self._simple_plan(request, hint)
        if self.config.model.provider == "mock":
            return self._heuristic_plan(request, goal)
        return await self._llm_plan(request, goal)

    async def execute(self, request: TaskRequest) -> TaskResult:
        """Execute planning and return the plan wrapped in a TaskResult."""
        plan = await self.plan(request)
        output = _plan_to_dict(plan)
        agent_id = request.input.get("agent_id") if request.input else None
        result = TaskResult.success(request.task_id, output, agent_id=self.agent_id)
        result.metrics = {
            "tasks": len(plan.tasks),
            "strategy": plan.strategy.value,
            "has_cycles": plan.has_cycles(),
        }
        return result

    async def stream(self, request: TaskRequest):
        """Stream plan progress deltas then the final plan."""
        from agentforge_agents.schemas.events import EventType, ExecutionEvent
        from agentforge_agents.utils.ids import new_id

        plan = await self.plan(request)
        steps = len(plan.tasks)
        for index in range(steps):
            yield ExecutionEvent.create(
                EventType.TASK_PROGRESS,
                task_id=request.task_id,
                agent_id=self.agent_id,
                session_id=self.context.session_id,
                payload={
                    "progress": (index + 1) / max(steps, 1),
                    "phase": "planning",
                    "step": index + 1,
                },
            )
        yield ExecutionEvent.create(
            EventType.TASK_COMPLETED,
            task_id=request.task_id,
            agent_id=self.agent_id,
            session_id=self.context.session_id,
            payload={"plan": _plan_to_dict(plan), "event_id": new_id("evt")},
        )

    async def _llm_plan(self, request: TaskRequest, goal: str) -> PlannerResponse:
        from agentforge_agents.schemas.common import Message

        messages = [
            Message.system(self.config.system_prompt or "You are the Planner Agent."),
            Message.user(
                f"Produce a JSON plan for this request:\n{goal}\n\n"
                "Return strict JSON with keys goal, strategy, tasks "
                "(each: id, agent_id, instruction, input, depends_on), rationale."
            ),
        ]
        raw = await self._generate_text(messages)
        parsed = _try_parse_plan(raw, request.task_id, goal)
        if parsed is not None:
            return parsed
        log.warning("planner_llm_output_unparsed_falling_back")
        return self._heuristic_plan(request, goal)

    def _heuristic_plan(self, request: TaskRequest, goal: str) -> PlannerResponse:
        """Deterministic plan: split sentences into sequential tasks."""
        sentences = [s.strip() for s in goal.replace("\n", " ").split(". ") if s.strip()][:5] or [
            goal
        ]
        from agentforge_agents.schemas.planning import PlanDependency, PlanTask

        router = _module_router()
        plan_tasks: list[PlanTask] = []
        dependencies: list[PlanDependency] = []
        previous: str | None = None
        for index, sentence in enumerate(sentences):
            task_id = f"t{index + 1}"
            plan_tasks.append(
                PlanTask(
                    id=task_id,
                    agent_id=router(sentence),
                    instruction=sentence,
                    input=dict(request.input),
                    priority=len(sentences) - index,
                    depends_on=[previous] if previous else [],
                )
            )
            if previous:
                dependencies.append(
                    PlanDependency(source=previous, target=task_id, kind="requires")
                )
            previous = task_id
        return PlannerResponse(
            request_id=request.task_id,
            goal=goal,
            tasks=plan_tasks,
            dependencies=dependencies,
            rationale="Heuristic sentence-level decomposition.",
            total_estimated_tasks=len(plan_tasks),
        )


_capability_order = [
    "planner",
    "coding",
    "research",
    "data",
    "automation",
    "browser",
    "document",
    "memory",
    "workflow",
    "communication",
]


def _module_router():
    """Build a lightweight keyword router independent of an AgentRegistry."""
    from agentforge_agents.orchestration.router import AgentRouter, RoutingRule

    rules = [
        RoutingRule(
            "coding", ("code", "python", "typescript", "bug", "refactor", "function", "sql", "bash")
        ),
        RoutingRule("research", ("research", "search", "citations", "find out")),
        RoutingRule("data", ("data", "dataset", "pandas", "statistics", "cleaning", "csv")),
        RoutingRule("document", ("pdf", "docx", "report", "memo", "spreadsheet")),
        RoutingRule("communication", ("email", "slack", "notification", "meeting")),
        RoutingRule("automation", ("automate", "schedule", "integration")),
        RoutingRule("memory", ("remember", "recall", "memory")),
        RoutingRule("browser", ("website", "web page", "screenshot", "browse")),
    ]
    return AgentRouter(None, rules, default_agent="planner").route_text  # type: ignore[arg-type]


def _plan_to_dict(plan: PlannerResponse) -> dict[str, Any]:
    return {
        "goal": plan.goal,
        "strategy": plan.strategy.value,
        "tasks": [task.model_dump() for task in plan.tasks],
        "dependencies": [dep.model_dump() for dep in plan.dependencies],
        "rationale": plan.rationale,
        "total_estimated_tasks": plan.total_estimated_tasks,
        "execution_order": plan.execution_order(),
    }


def _try_parse_plan(raw: str, request_id: str, goal: str) -> PlannerResponse | None:
    """Best-effort tolerant JSON extraction from an LLM response."""
    import json

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        data = json.loads(raw[start:end])
        tasks = []
        for item in data.get("tasks", []):
            item.setdefault("agent_id", "planner")
            item.setdefault("input", {})
            item.setdefault("depends_on", [])
            tasks.append(item)
        return PlannerResponse(
            request_id=request_id,
            goal=data.get("goal") or goal,
            strategy=data.get("strategy", "sequential"),
            tasks=tasks,
            rationale=data.get("rationale"),
            total_estimated_tasks=len(tasks),
        )
    except Exception:  # noqa: BLE001
        return None


__all__ = ["Agent"]
