"""Production orchestrator - plans, routes, executes, aggregates, and supervises."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from agentforge_agents.core.registry import AgentRegistry
from agentforge_agents.orchestration.aggregator import DelegationManager, ResponseAggregator
from agentforge_agents.orchestration.checkpoint import CheckpointManager
from agentforge_agents.orchestration.parallel import ParallelExecutor
from agentforge_agents.orchestration.planner import TaskPlanner
from agentforge_agents.orchestration.router import AgentRouter
from agentforge_agents.orchestration.state_machine import TaskStateMachine
from agentforge_agents.orchestration.supervisor import Supervisor
from agentforge_agents.schemas.events import EventType, ExecutionEvent
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult, TaskStatus
from agentforge_agents.utils.errors import OrchestrationError
from agentforge_agents.utils.ids import new_id
from agentforge_agents.utils.logging import get_logger

if TYPE_CHECKING:
    from agentforge_agents.events.bus import EventBus

log = get_logger(__name__)


class Orchestrator:
    """Coordinates multi-agent runs from a request to an aggregated result.

    Pipeline: ``route -> plan -> execute (DAG, parallel, retried) -> aggregate``.

    ``run`` executes a plan to completion; ``stream`` yields events during it so
    clients can render live progress.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        *,
        events: EventBus | None = None,
        router: AgentRouter | None = None,
        planner: TaskPlanner | None = None,
        parallel: ParallelExecutor | None = None,
        aggregator: ResponseAggregator | None = None,
        supervisor: Supervisor | None = None,
        checkpoint: CheckpointManager | None = None,
        max_concurrency: int = 4,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.events = events
        self.router = router or AgentRouter(self.registry)
        self.planner = planner or TaskPlanner()
        self.parallel = parallel or ParallelExecutor(max_concurrency=max_concurrency)
        self.aggregator = aggregator or ResponseAggregator()
        self.supervisor = supervisor or Supervisor()
        self.checkpoint = checkpoint or CheckpointManager()
        self.delegator = DelegationManager()
        self.context = None

    # ------------------------------------------------------------ planning
    async def plan(self, request: TaskRequest, **planner_kwargs: Any) -> PlannerResponse:
        """Plan a request using the planner agent (or heuristic fallback)."""
        if self.events is not None:
            await self.events.publish(
                ExecutionEvent.create(
                    EventType.ORCHESTRATOR_PLAN,
                    task_id=request.task_id,
                    session_id=request.context.get("session_id"),
                    payload={"goal": request.instructions or request.text_input()},
                )
            )
        if self.registry.has("planner"):
            plan = await self._plan_with_agent(request)
            return plan or self._heuristic_plan(request, **planner_kwargs)
        return self._heuristic_plan(request, **planner_kwargs)

    async def _plan_with_agent(self, request: TaskRequest) -> PlannerResponse | None:
        agent = self.registry.instantiate(
            "planner",
            context=self.context,
            tool_registry=getattr(self, "tool_registry", None),
            memory=getattr(self, "memory", None),
            events=self.events,
        )
        try:
            plan = await agent.plan(request)
        except Exception as exc:  # noqa: BLE001
            log.warning("planner_agent_failed_falling_back", error=str(exc))
            return None
        return plan

    async def _heuristic_plan(self, request: TaskRequest, **kwargs: Any) -> PlannerResponse:
        return await self.planner.plan(
            request_id=request.task_id,
            goal=request.instructions or request.text_input(),
            input_data=request.input,
            agent_hints=kwargs.get("agent_hints"),
            strategy=kwargs.get("strategy"),
        )

    # ------------------------------------------------------------ routing
    def route(self, request: TaskRequest) -> str:
        agent_id = self.router.route_request(request)
        log.info("task_routed", task_id=request.task_id, agent_id=agent_id)
        return agent_id

    # ------------------------------------------------------------ execution
    async def execute(
        self, request: TaskRequest, *, plan: PlannerResponse | None = None
    ) -> TaskResult:
        """Execute ``request`` and return the aggregated result."""
        request_id = request.task_id or new_id("task")
        resolved = plan or await self.plan(request)
        results = await self._run_plan(resolved, request_id)
        successful = [r for r in results.values() if r.ok()]
        if not successful:
            first = next(iter(results.values()), None)
            if first is None:
                raise OrchestrationError("plan produced no results", task_id=request_id)
            return TaskResult.failure(request_id, first.error or "all tasks failed", agent_id=None)
        merged = self.aggregator.merge(successful)
        return TaskResult(
            task_id=request_id,
            agent_id=request.agent_id or request.context.get("agent_id"),
            status=TaskStatus.COMPLETED,
            output=merged,
            metrics={"tasks_completed": len(successful), "tasks_total": len(results)},
        )

    async def _run_plan(self, plan: PlannerResponse, request_id: str) -> dict[str, TaskResult]:
        """Execute plan layers respecting the dependency graph and retrying failures."""
        layers = plan.execution_order()
        completed: dict[str, TaskResult] = {}
        for layer_index, layer_ids in enumerate(layers):
            log.info("plan_layer_start", request_id=request_id, layer=layer_index, tasks=layer_ids)
            layer_results = await self.parallel.run_plan(
                layer_ids,
                lambda task_id: self._execute_plan_task(plan, task_id, request_id, completed),
            )
            completed.update(layer_results)
            if self.events is not None:
                await self.events.publish(
                    ExecutionEvent.create(
                        EventType.TASK_PROGRESS,
                        task_id=request_id,
                        payload={"layer": layer_index, "completed": list(layer_results)},
                    )
                )
        return completed

    async def _execute_plan_task(
        self,
        plan: PlannerResponse,
        task_id: str,
        request_id: str,
        completed: dict[str, TaskResult],
    ) -> TaskResult:
        plan_task = next(t for t in plan.tasks if t.id == task_id)
        agent_id = plan_task.agent_id
        task_request = TaskRequest(
            task_id=task_id,
            agent_id=agent_id,
            input=plan_task.input,
            instructions=plan_task.instruction,
            parent_task_id=request_id,
            context={**plan_task.metadata, "session_id": request_id},
        )
        result = await self._run_task_with_recovery(task_request)
        self.delegator.register_output(task_id, result.output)
        return result

    async def _run_task_with_recovery(self, request: TaskRequest) -> TaskResult:
        state_machine = TaskStateMachine()
        state_machine.transition("scheduled", reason="orchestrator dispatch")
        state_machine.transition("running")
        for _ in range(self.supervisor.policy.max_failures + 1):
            result = await self._dispatch(request)
            verdict = self.supervisor.review(request.task_id, result)
            if verdict["action"] == "retry":
                state_machine.transition("retrying")
                state_machine.transition("running", reason=verdict["reason"])
                continue
            break
        return result

    async def _dispatch(self, request: TaskRequest) -> TaskResult:
        if not self.registry.has(request.agent_id or ""):
            return TaskResult.failure(request.task_id, f"unknown agent {request.agent_id!r}")
        agent = self.registry.instantiate(
            request.agent_id,
            context=self.context,
            tool_registry=getattr(self, "tool_registry", None),
            memory=getattr(self, "memory", None),
            events=self.events,
        )
        agent.context.metadata["task_id"] = request.task_id
        return await agent.run(request)

    async def run_agent(self, agent_id: str, request: TaskRequest) -> TaskResult:
        """Execute a single agent directly (orchestrator bypass)."""
        request.agent_id = agent_id
        return await self._run_task_with_recovery(request)

    # ------------------------------------------------------------ streaming
    async def stream(self, request: TaskRequest) -> AsyncIterator[ExecutionEvent]:
        """Yield orchestrator-level events while executing ``request``."""
        request_id = request.task_id
        if self.events is not None:
            await self.events.publish(
                ExecutionEvent.create(
                    EventType.TASK_STARTED,
                    task_id=request_id,
                    session_id=request.context.get("session_id"),
                )
            )
        try:
            result = await self.execute(request)
            yield ExecutionEvent.create(
                EventType.TASK_COMPLETED,
                task_id=request_id,
                payload={
                    "result": result.model_dump() if hasattr(result, "model_dump") else result
                },
            )
        except Exception as exc:  # noqa: BLE001
            yield ExecutionEvent.create(
                EventType.TASK_FAILED, task_id=request_id, payload={"error": str(exc)}
            )

    # ---------------------------------------------------------- checkpointing
    async def save_checkpoint(self, run_id: str, **state: Any) -> None:
        await self.checkpoint.save(run_id, state)

    async def resume(self, run_id: str) -> dict[str, Any] | None:
        return await self.checkpoint.load(run_id)

    async def close(self) -> None:
        pass


__all__ = ["Orchestrator"]
