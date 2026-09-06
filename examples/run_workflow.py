#!/usr/bin/env python3
"""Example 4: Execute a workflow with the Workflow agent."""

from agentforge_agents.config.loader import bootstrap
from agentforge_agents.core.context import RuntimeContext
from agentforge_agents.schemas.task import TaskRequest
from agentforge_agents.tools import build_registry
from agentforge_agents.utils.ids import new_id


def main() -> None:
    result = bootstrap()
    registry, permissions, memory, events, telemetry = (
        result.registry,
        result.permissions,
        result.memory,
        result.events,
        result.telemetry,
    )
    tool_registry = build_registry(permissions=permissions)
    context = RuntimeContext(session_id=new_id("session"), metadata={"task_id": new_id("task")})
    agent = registry.instantiate(
        "workflow",
        context=context,
        tool_registry=tool_registry,
        memory=memory,
        events=events,
        telemetry=telemetry,
    )

    steps = [
        {"id": "setup", "step_type": "inline", "input": {"env": "production"}},
        {"id": "build", "step_type": "delay", "delay_seconds": 0.1},
        {"id": "test", "step_type": "inline", "input": {"test": "unit"}},
    ]
    request = TaskRequest(
        task_id=new_id("task"),
        agent_id="workflow",
        instructions="run workflow",
        input={"workflow": {"steps": steps}},
    )
    task_result = agent.run(request)
    import asyncio

    task_result = asyncio.run(task_result)
    print(f"Status: {task_result.status}")
    print(f"Run ID: {task_result.output.get('run_id')}")
    for sr in task_result.output.get("step_results", []):
        print(f"  {sr['step_id']}: {sr['status']}")


if __name__ == "__main__":
    main()
