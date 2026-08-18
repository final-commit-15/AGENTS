import logging
from typing import Dict, Type, Optional, List
from app.agents.base.agent import BaseAgent
from app.agents.base.config import AgentConfig

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for all agent classes and configurations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, Type[BaseAgent]] = {}
            cls._instance._configs: Dict[str, AgentConfig] = {}
        return cls._instance

    def register(self, agent_class: Type[BaseAgent], config: AgentConfig):
        """Register an agent class with its configuration."""
        agent_id = config.id or agent_class.__name__.lower()
        self._agents[agent_id] = agent_class
        self._configs[agent_id] = config
        logger.info(f"Registered agent: {agent_id} (version {config.version})")

    def get_agent_class(self, agent_id: str) -> Type[BaseAgent]:
        """Retrieve an agent class by ID."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found in registry.")
        return self._agents[agent_id]

    def get_config(self, agent_id: str) -> AgentConfig:
        """Retrieve configuration for an agent."""
        if agent_id not in self._configs:
            raise KeyError(f"Config for agent '{agent_id}' not found.")
        return self._configs[agent_id]

    def list_agents(self) -> List[str]:
        """List all registered agent IDs."""
        return list(self._agents.keys())

    def get_all_configs(self) -> Dict[str, AgentConfig]:
        return self._configs.copy()