#!/usr/bin/env python3
"""Example 6: Multi-agent orchestration via the Orchestrator."""

from agentforge_agents.config.loader import bootstrap
from agentforge_agents.orchestration.executor import Orchestrator
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

    orch = Orchestrator(
        registry=registry,
        tool_registry=tool_registry,
        memory=memory,
        events=events,
        telemetry=telemetry,
    )

    request = TaskRequest(
        task_id=new_id("task"),
        instructions="Plan a Python CLI tool, implement it, write a README, and create a GitHub repo",
    )
    task_result = orch.run(request)
    import asyncio

    task_result = asyncio.run(task_result)
    print(f"Status: {task_result.status}")
    print(f"Output: {task_result.output}")


if __name__ == "__main__":
    main()
