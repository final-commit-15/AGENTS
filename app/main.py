import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agents.registry.loader import AgentLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgentForge Agents",
    version="1.0.0",
)

# Load all configured agents
loader = AgentLoader(config_dir="configs/agents/")
loader.load_all()

registry = loader.registry
loaded_agents = registry.list_agents()

if not loaded_agents:
    raise RuntimeError("No agents were loaded")

logger.info("Registered agents: %s", loaded_agents)


class ExecuteRequest(BaseModel):
    agent_id: str
    input: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agents": loaded_agents,
    }


@app.get("/agents")
async def list_agents():
    return {
        "agents": loaded_agents,
    }


@app.post("/execute")
async def execute_agent(request: ExecuteRequest):
    try:
        agent_class = registry.get_agent_class(request.agent_id)
        config = registry.get_config(request.agent_id)

        if not config.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{request.agent_id}' is disabled",
            )

        agent = agent_class(config)

        result = await agent.run(request.input)

        if hasattr(result, "model_dump"):
            return result.model_dump()

        return result

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Agent execution failed: %s",
            request.agent_id,
        )
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc