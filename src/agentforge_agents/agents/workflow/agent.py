"""Workflow Agent - executes pipelines, DAGs, retries, and checkpoints."""

from __future__ import annotations

from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.common import Message
from agentforge_agents.schemas.planning import PlannerResponse
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.schemas.workflow import StepResult, WorkflowRun
from agentforge_agents.utils.ids import new_id
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Agent(BaseAgent):
    """Interprets and runs :class:`WorkflowDefinition` objects step by step."""

    @property
    def default_tools(self) -> list[str]:
        return ["filesystem", "http", "terminal", "python_runner"]

    async def plan(self, request: TaskRequest) -> PlannerResponse:
        return self._simple_plan(request, "workflow")

    async def execute(self, request: TaskRequest) -> TaskResult:
        workflow = request.input.get("workflow", {}) if request.input else {}
        steps = workflow.get("steps", [])
        if not steps:
            return await self._generate_workflow(request)
        return await self._run_steps(request, steps)

    async def _run_steps(self, request: TaskRequest, steps: list[dict[str, Any]]) -> TaskResult:
        run = WorkflowRun(run_id=new_id("run"), workflow_id=request.task_id)
        for step in steps:
            run.current_step = step.get("id", "?")
            result = await self._execute_step(step, run.state)
            run.step_results.append(
                StepResult(
                    step_id=run.current_step,
                    output=result.output,
                    error=result.error,
                    status="completed" if result.success else "failed",
                )
            )
            if step.get("output_key"):
                run.state[step["output_key"]] = result.output
            if not result.success:
                run.set_status("failed")
                run.error = result.error
                return TaskResult(
                    task_id=request.task_id,
                    agent_id=self.agent_id,
                    output={
                        "run_id": run.run_id,
                        "step_results": [r.model_dump() for r in run.step_results],
                        "state": run.state,
                    },
                    status="failed",
                    error=run.error,
                )
        run.set_status("completed")
        return TaskResult.success(
            request.task_id,
            {
                "run_id": run.run_id,
                "step_results": [r.model_dump() for r in run.step_results],
                "state": run.state,
            },
            agent_id=self.agent_id,
        )

    async def _execute_step(self, step: dict[str, Any], state: dict[str, Any]) -> _StepOutcome:
        if step.get("tool_name"):
            result = await self._call_tool(
                str(step["tool_name"]), _resolve_input(step.get("input", {}), state)
            )
            return _StepOutcome(success=result.success, output=result.output, error=result.error)
        if step.get("delay_seconds"):
            import asyncio

            await asyncio.sleep(min(float(step["delay_seconds"]), 30))
            return _StepOutcome(success=True, output=None, error=None)
        if step.get("step_type") == "conditional" and step.get("expression"):
            return _StepOutcome(
                success=True,
                output=bool(_evaluate_expression(step["expression"], state)),
                error=None,
            )
        return _StepOutcome(success=True, output=step.get("input", {}), error=None)

    async def _generate_workflow(self, request: TaskRequest) -> TaskResult:
        task = request.instructions or request.text_input()
        if self.config.model.provider == "mock":
            return TaskResult.success(
                request.task_id,
                {"workflow": _mock_workflow(task)},
                agent_id=self.agent_id,
            )
        messages = [
            Message.system(self.config.system_prompt or "You are the Workflow Agent."),
            Message.user("Design a workflow definition for:\n" + task),
        ]
        definition = await self._generate_text(messages)
        return TaskResult.success(request.task_id, {"workflow": definition}, agent_id=self.agent_id)


def _resolve_input(input_template: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (state.get(value[2:]) if isinstance(value, str) and value.startswith("$s.") else value)
        for key, value in input_template.items()
    }


from dataclasses import dataclass


@dataclass
class _StepOutcome:
    success: bool
    output: Any
    error: str | None = None


def _evaluate_expression(expression: str, state: dict[str, Any]) -> bool:
    token = expression.strip().lstrip("$s.").split(".")[0]
    return bool(state.get(token))


def _mock_workflow(task: str) -> str:
    return f"1. gather inputs 2. process ({task[:80]}) 3. report"


__all__ = ["Agent"]
