"""FastAPI application exposing agents, health, and task execution over HTTP."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agentforge_agents.config.loader import BootstrapResult, bootstrap
from agentforge_agents.core.context import RuntimeContext
from agentforge_agents.schemas.task import TaskRequest, TaskResult
from agentforge_agents.tools import build_registry
from agentforge_agents.tools.registry import ToolRegistry
from agentforge_agents.utils.ids import new_id
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)

app_components: BootstrapResult | None = None
_tool_registry: ToolRegistry | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global app_components, _tool_registry
    app_components = bootstrap()
    _tool_registry = build_registry(permissions=app_components.permissions)
    log.info("server_started", agents=app_components.registry.list_agents())
    yield
    app_components = None
    _tool_registry = None


app = FastAPI(
    title="AgentForge Agents API",
    version="1.0.0",
    description="Modular multi-agent execution and orchestration service.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require() -> BootstrapResult:
    if app_components is None:
        raise HTTPException(status_code=503, detail="service not booted")
    return app_components


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness + readiness probe combining service and dependency state."""
    components = _require()
    registry = components.registry
    return {
        "status": "ok",
        "service": "agentforge-agents",
        "version": "1.0.0",
        "agents": len(registry.list_agents()),
        "dependencies": {
            "agents": registry.list_agents(),
            "event_bus": components.events.backend_type(),
            "memory": {"backend": components.settings.memory_backend},
        },
    }


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, Any]:
    components = _require()
    return {"status": "ok", "agents": len(components.registry.list_agents())}


@app.get("/agents")
async def list_agents() -> dict[str, Any]:
    components = _require()
    agents = components.registry.list_agents()
    return {"agents": agents, "count": len(agents)}


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict[str, Any]:
    components = _require()
    if not components.registry.has(agent_id):
        raise HTTPException(status_code=404, detail=f"unknown agent {agent_id!r}")
    config = components.registry.get_config(agent_id)
    return config.model_dump(mode="json")


@app.get("/tools")
async def list_tools() -> dict[str, Any]:
    if _tool_registry is None:
        raise HTTPException(status_code=503, detail="service not booted")
    return {"tools": _tool_registry.names(), "count": len(_tool_registry)}


@app.post("/tasks", response_model=TaskResult)
async def run_task(request: TaskRequest) -> TaskResult:
    """Execute a single task against a target agent."""
    components = _require()
    if _tool_registry is None:
        raise HTTPException(status_code=503, detail="service not booted")
    agent_id = request.agent_id or "planner"
    if not components.registry.has(agent_id):
        raise HTTPException(status_code=404, detail=f"unknown agent {agent_id!r}")
    if not request.task_id:
        request.task_id = new_id("task")
    context = RuntimeContext(
        session_id=new_id("session"),
        namespace=(
            (request.context or {}).get("namespace", "default") if request.context else "default"
        ),
        metadata={"task_id": request.task_id},
    )
    agent = components.registry.instantiate(
        agent_id,
        context=context,
        tool_registry=_tool_registry,
        memory=components.memory,
        events=components.events,
        telemetry=components.telemetry,
    )
    return await agent.run(request)


__all__ = ["app"]
