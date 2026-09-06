"""AgentLoader - loads YAML configs and package prompts, with hot reload."""

from __future__ import annotations

import importlib.resources
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agentforge_agents.core.registry import AgentRegistry
from agentforge_agents.prompts.manager import PromptManager
from agentforge_agents.schemas.agent import AgentConfig
from agentforge_agents.utils.errors import ConfigError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class _WatchEntry:
    """Hot-reload watch state for a single agent config file."""

    path: Path
    mtime: float


class AgentLoader:
    """Loads agent definitions from YAML plus packaged ``prompt.md`` files.

    Two sources are supported:

    * Filesystem: ``config_dir`` containing ``<agent_id>.yaml`` files.
    * Packages: YAML embedded next to each agent package (used when the
      filesystem dir is empty or the ``package`` source is requested).

    Hot reload polls ``config_dir`` every ``reload_interval`` seconds and
    re-registers changed configs in place.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        *,
        config_dir: str | os.PathLike[str] | None = None,
        package_source: str = "agentforge_agents.agents",
        package_data: str = "config.yaml",
        prompt_manager: PromptManager | None = None,
        reload_interval: float = 5.0,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.config_dir = Path(config_dir) if config_dir else None
        self.package_source = package_source
        self.package_data = package_data
        self.prompts = prompt_manager or PromptManager()
        self.reload_interval = reload_interval
        self._watches: dict[str, _WatchEntry] = {}

    # ------------------------------------------------------------ loading
    def load_all(self) -> AgentRegistry:
        """Load every agent configured on the filesystem (falling back to packages)."""
        loaded = (
            self._load_from_packages() if self.config_dir is None else self._load_from_directory()
        )
        log.info("agents_loaded", count=len(loaded), agents=loaded)
        return self.registry

    def load_agent(self, agent_id: str) -> AgentConfig:
        self._watches.pop(agent_id, None)
        path = self.config_dir / f"{agent_id}.yaml" if self.config_dir else None
        if path is not None and path.is_file():
            yaml_data = _read_yaml(path)
            self._watches[agent_id] = _WatchEntry(path=path, mtime=path.stat().st_mtime)
        else:
            yaml_data = _read_package_yaml(self.package_source, agent_id, self.package_data)
        return self._register_from_data(agent_id, yaml_data)

    def _load_from_directory(self) -> list[str]:
        assert self.config_dir is not None
        if not self.config_dir.is_dir():
            log.warning("config_dir_missing", path=str(self.config_dir))
            return []
        agents: list[str] = []
        for name in sorted(self.config_dir.glob("*.y*ml")):
            agent_id = name.stem
            yaml_data = _read_yaml(name)
            self._watches[agent_id] = _WatchEntry(path=name, mtime=name.stat().st_mtime)
            self._register_from_data(agent_id, yaml_data)
            agents.append(agent_id)
        return agents

    def _load_from_packages(self) -> list[str]:
        agents: list[str] = []
        package = importlib.import_module(self.package_source)
        for directory in Path(package.__file__).parent.iterdir():  # type: ignore[arg-type]
            if not directory.is_dir():
                continue
            if not (directory / self.package_data).is_file():
                continue
            agent_id = directory.name
            yaml_data = _read_yaml(directory / self.package_data)
            self._register_from_data(agent_id, yaml_data)
            agents.append(agent_id)
        return agents

    def _register_from_data(self, agent_id: str, yaml_data: dict[str, Any]) -> AgentConfig:
        try:
            config = AgentConfig(**yaml_data)
        except Exception as exc:
            raise ConfigError(f"invalid agent config for {agent_id!r}: {exc}") from exc
        from agentforge_agents.core.base import BaseAgent

        agent_class = _dotted_import(config.agent_class)
        if not (isinstance(agent_class, type) and issubclass(agent_class, BaseAgent)):
            raise ConfigError(f"agent {agent_id!r} class must be a BaseAgent subclass")
        self.registry.register(config, agent_class)
        return config

    # --------------------------------------------------------- hot reload
    def reload_if_changed(self) -> list[str]:
        """Re-register configs whose files changed since the last check."""
        if self.config_dir is None:
            return []
        changed: list[str] = []
        for agent_id, entry in list(self._watches.items()):
            try:
                mtime = entry.path.stat().st_mtime
            except OSError:
                continue
            if mtime != entry.mtime:
                log.info("agent_config_reloaded", agent_id=agent_id)
                self.load_agent(agent_id)
                changed.append(agent_id)
        return changed

    async def watch_loop(self):  # pragma: no cover - lifecycle utility
        """Poll for config changes forever (run as an asyncio task)."""
        import asyncio

        while True:
            self.reload_if_changed()
            await asyncio.sleep(self.reload_interval)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"agent config must be a mapping: {path}")
    return data


def _read_package_yaml(package: str, agent_id: str, data_file: str) -> dict[str, Any]:
    try:
        text = (importlib.resources.files(package) / agent_id / data_file).read_text(
            encoding="utf-8"
        )
    except FileNotFoundError as exc:
        raise ConfigError(f"no config.yaml for agent {agent_id!r} in package {package}") from exc
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"agent config must be a mapping: {agent_id}")
    return data


def _dotted_import(path: str) -> Any:
    module_name, _, member_name = path.rpartition(".")
    if not module_name:
        raise ConfigError(f"invalid dotted class path: {path!r}")
    module = importlib.import_module(module_name)
    return getattr(module, member_name)


__all__ = ["AgentLoader"]
