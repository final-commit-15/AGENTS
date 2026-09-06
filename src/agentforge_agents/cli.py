"""CLI entrypoint ``agentforge-agents`` for serving and inspecting the runtime."""

from __future__ import annotations

import argparse
import asyncio
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentforge-agents",
        description="AgentForge agents service - serve the API or run one-off commands.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the FastAPI server.")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--workers", type=int, default=1)
    serve.add_argument("--reload", action="store_true", help="Enable auto-reload (dev).")

    run = sub.add_parser("run", help="Execute a single task against an agent.")
    run.add_argument("--agent", default="planner", help="Target agent id.")
    run.add_argument("--task-id", default=None)
    run.add_argument("task_text", help="The task instructions.")

    ls = sub.add_parser("list", help="List registered agents.")
    ls.add_argument("--json", action="store_true", help="Emit JSON.")

    return parser


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "agentforge_agents.server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
    )
    return 0


def _run(args: argparse.Namespace) -> int:
    from agentforge_agents.config.loader import bootstrap
    from agentforge_agents.core.context import RuntimeContext
    from agentforge_agents.schemas.task import TaskRequest
    from agentforge_agents.tools import build_registry
    from agentforge_agents.utils.ids import new_id

    result = bootstrap()
    registry, permissions, memory, events, telemetry = (
        result.registry,
        result.permissions,
        result.memory,
        result.events,
        result.telemetry,
    )
    if not registry.has(args.agent):
        print(
            f"error: unknown agent {args.agent!r}; choose from {registry.list_agents()}",
            file=sys.stderr,
        )
        return 2
    tool_registry = build_registry(permissions=permissions)
    context = RuntimeContext(
        session_id=new_id("session"), metadata={"task_id": args.task_id or new_id("task")}
    )
    agent = registry.instantiate(
        args.agent,
        context=context,
        tool_registry=tool_registry,
        memory=memory,
        events=events,
        telemetry=telemetry,
    )
    request = TaskRequest(
        task_id=args.task_id or new_id("task"), agent_id=args.agent, instructions=args.task_text
    )
    task_result = asyncio.run(agent.run(request))
    print(task_result.model_dump_json(indent=2))
    return 0 if task_result.ok() else 1


def _list(args: argparse.Namespace) -> int:
    from agentforge_agents.config.loader import bootstrap

    result = bootstrap()
    agents = result.registry.list_agents()
    if args.json:
        import json

        print(json.dumps(agents))
    else:
        for agent_id in agents:
            print(agent_id)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        raise SystemExit(_serve(args))
    if args.command == "run":
        raise SystemExit(_run(args))
    if args.command == "list":
        raise SystemExit(_list(args))
    parser.print_help()
    raise SystemExit(1)


__all__ = ["main"]
