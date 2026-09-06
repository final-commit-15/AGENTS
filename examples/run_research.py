#!/usr/bin/env python3
"""Example 5: Research a topic with the Research agent."""

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
        "research",
        context=context,
        tool_registry=tool_registry,
        memory=memory,
        events=events,
        telemetry=telemetry,
    )
    request = TaskRequest(
        task_id=new_id("task"),
        agent_id="research",
        instructions="Research the benefits of async programming in Python",
    )
    task_result = agent.run(request)
    import asyncio

    task_result = asyncio.run(task_result)
    print(f"Status: {task_result.status}")
    if task_result.output:
        print(f"Report: {str(task_result.output)[:500]}")


if __name__ == "__main__":
    main()
