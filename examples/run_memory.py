#!/usr/bin/env python3
"""Example 3: Store and retrieve memory using the Memory agent."""

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
        "memory",
        context=context,
        tool_registry=tool_registry,
        memory=memory,
        events=events,
        telemetry=telemetry,
    )

    store = TaskRequest(
        task_id=new_id("task"),
        agent_id="memory",
        instructions="store",
        input={
            "operation": "store",
            "content": "The project uses Python 3.12 and FastAPI",
            "kind": "project",
        },
    )
    recall = TaskRequest(
        task_id=new_id("task"),
        agent_id="memory",
        instructions="recall",
        input={"operation": "recall", "query": "project language", "limit": 5},
    )

    import asyncio

    r1 = asyncio.run(agent.run(store))
    r2 = asyncio.run(agent.run(recall))
    print(f"Store: {r1.status}, {r1.output}")
    print(f"Recall: {r2.status}, hits={r2.output.get('count', 0)}")
    for hit in r2.output.get("hits", []):
        print(f"  - {hit['content'][:80]} (score={hit['score']:.2f})")


if __name__ == "__main__":
    main()
