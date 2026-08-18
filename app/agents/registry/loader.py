"""
Dynamic agent loader that reads YAML configurations and registers agent classes.

Uses importlib to load agent classes from the configured module path.
"""

import importlib
import logging
import os
from typing import Dict, Any, Optional

import yaml

from .registry import AgentRegistry
from ..base.config import AgentConfig
from ..base.agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Loads agent configurations from YAML files and registers them
    into the AgentRegistry.
    """

    def __init__(self, config_dir: str = "configs/agents/"):
        """
        Initialize the loader with the directory containing YAML configs.

        Args:
            config_dir: Path to the directory (relative to project root)
                       containing agent YAML files.
        """
        self.config_dir = config_dir
        self.registry = AgentRegistry()

    def load_all(self) -> None:
        """
        Scan the config directory and load every .yaml or .yml file.
        """
        if not os.path.exists(self.config_dir):
            logger.warning(f"Config directory {self.config_dir} not found.")
            return

        for filename in os.listdir(self.config_dir):
            if filename.endswith((".yaml", ".yml")):
                filepath = os.path.join(self.config_dir, filename)
                try:
                    self.load_from_file(filepath)
                except Exception as e:
                    logger.error(f"Failed to load {filepath}: {e}", exc_info=True)

    def load_from_file(self, filepath: str) -> None:
        """
        Load a single YAML file and register its agent.

        Args:
            filepath: Full path to the YAML file.

        Raises:
            ValueError: If agent ID or name is missing.
            TypeError: If the loaded class is not a subclass of BaseAgent.
            ImportError: If the module or class cannot be imported.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        agent_id = data.get("id") or data.get("name")
        if not agent_id:
            raise ValueError(f"Agent ID or name missing in {filepath}")
        agent_id = agent_id.lower()

        # Build AgentConfig from YAML data
        config = AgentConfig(**data)

        # Determine module and class names
        module_name = data.get("module")
        class_name = data.get("class")

        if not module_name:
            # fallback: app.agents.built_in.<agent_id>
            module_name = f"app.agents.built_in.{agent_id.replace('-', '_')}"
        if not class_name:
            # fallback: capitalize and replace hyphens
            class_name = ''.join(word.capitalize() for word in agent_id.split('-'))

        # Import the class
        try:
            module = importlib.import_module(module_name)
            agent_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Could not import {class_name} from {module_name}")
            raise ImportError(f"Failed to load agent class for {agent_id}") from e

        # Validate it's a BaseAgent subclass
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{class_name} must be a subclass of BaseAgent")

        # Register
        self.registry.register(agent_class, config)
        logger.info(f"Loaded agent: {agent_id} (version {config.version})")