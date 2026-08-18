import logging
import os
import time

from app.agents.registry.loader import AgentLoader

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("agentforge-agents")


def main() -> None:
    logger.info("Starting AgentForge Agents service")

    loader = AgentLoader(config_dir="configs/agents/")
    loader.load_all()

    loaded_agents = loader.registry.list_agents()

    logger.info("Registered agents: %s", loaded_agents)

    if not loaded_agents:
        raise RuntimeError("No agents were loaded")

    logger.info(
        "AgentForge Agents service ready with %d agent(s)",
        len(loaded_agents),
    )

    # Keep the worker container alive.
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()