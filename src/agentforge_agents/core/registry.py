"""Agent registry with dynamic registration and auto-discovery."""

from __future__ import annotations

import importlib
import inspect
from typing import Any

from agentforge_agents.core.base import BaseAgent
from agentforge_agents.schemas.agent import AgentConfig
from agentforge_agents.utils.errors import RegistryError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class AgentRegistry:
    """Holds all discoverable agent classes and their static configs."""

    def __init__(self) -> None:
        self._classes: dict[str, type[BaseAgent]] = {}
        self._configs: dict[str, AgentConfig] = {}

    # ------------------------------------------------------------- mutation
    def register(self, config: AgentConfig, agent_class: type[BaseAgent]) -> None:
        """Register a validated agent. Re-registration overwrites silently."""
        if not (inspect.isclass(agent_class) and issubclass(agent_class, BaseAgent)):
            raise RegistryError(f"agent class for {config.id!r} must subclass BaseAgent")
        self._classes[config.id] = agent_class
        self._configs[config.id] = config
        log.info("agent_registered", agent_id=config.id, agent_class=agent_class.__module__)

    def unregister(self, agent_id: str) -> None:
        self._classes.pop(agent_id, None)
        self._configs.pop(agent_id, None)

    def register_module(self, module_path: str, agent_id: str | None = None) -> None:
        """Import ``module_path``, find a ``BaseAgent`` subclass and register it."""
        module = importlib.import_module(module_path)
        candidates = [
            member
            for _, member in inspect.getmembers(module, inspect.isclass)
            if issubclass(member, BaseAgent)
            and member is not BaseAgent
            and member.__module__ == module_path
        ]
        if not candidates:
            raise RegistryError(f"no BaseAgent subclass found in module {module_path!r}")
        if len(candidates) > 1:
            raise RegistryError(f"multiple agent classes in {module_path!r}: {candidates}")
        agent_class = candidates[0]
        resolved_id = agent_id
        if resolved_id is None:
            # Lowercase module leaf name, e.g. ``...agents.coding.agent`` -> ``coding``.
            resolved_id = module_path.rsplit(".", 1)[-1]
            if resolved_id == "agent":
                resolved_id = module_path.rsplit(".", 2)[-2]
        config = self._configs.get(resolved_id) or AgentConfig(
            id=resolved_id, name=resolved_id, agent_class=module_path
        )
        self.register(config, agent_class)

    # -------------------------------------------------------------- queries
    def get_agent_class(self, agent_id: str) -> type[BaseAgent]:
        try:
            return self._classes[agent_id]
        except KeyError:
            raise RegistryError(f"unknown agent: {agent_id!r}") from None

    def get_config(self, agent_id: str) -> AgentConfig:
        try:
            return self._configs[agent_id]
        except KeyError:
            raise RegistryError(f"unknown agent: {agent_id!r}") from None

    def get(self, agent_id: str) -> tuple[type[BaseAgent], AgentConfig]:
        return self.get_agent_class(agent_id), self.get_config(agent_id)

    def has(self, agent_id: str) -> bool:
        return agent_id in self._classes

    def list_agents(self) -> list[str]:
        return sorted(self._classes)

    def all_configs(self) -> list[AgentConfig]:
        return [self._configs[a] for a in self.list_agents()]

    def enabled_ids(self) -> list[str]:
        return [a for a, cfg in self._configs.items() if cfg.enabled]

    def instantiate(
        self,
        agent_id: str,
        *,
        context: Any = None,
        tool_registry: Any = None,
        memory: Any = None,
        events: Any = None,
        telemetry: Any = None,
    ) -> BaseAgent:
        """Create a configured, dependency-injected agent instance."""
        agent_class, config = self.get(agent_id)
        return agent_class(
            config,
            context=context,
            tool_registry=tool_registry,
            memory=memory,
            events=events,
            telemetry=telemetry,
        )

    # ---------------------------------------------------------- discovery
    def auto_discover(self, package: str, *, levels: list[str] | None = None) -> list[str]:
        """Register every ``agent`` module beneath ``package``.

        ``package`` must be a dotted import path. If ``levels`` is provided only
        those sub-package names are scanned.
        """
        import pkgutil

        base = importlib.import_module(package)
        discovered: list[str] = []
        for info in pkgutil.iter_modules(base.__path__):  # type: ignore[attr-defined]
            if levels is not None and info.name not in levels:
                continue
            subpackage = f"{package}.{info.name}"
            try:
                if info.ispkg:
                    importlib.import_module(f"{subpackage}.agent")
                    agent_module = f"{subpackage}.agent"
                else:
                    agent_module = subpackage
                self.register_module(agent_module, agent_id=info.name)
                discovered.append(info.name)
            except Exception as exc:  # noqa: BLE001
                log.warning("agent_discovery_skipped", module=subpackage, error=str(exc))
        return discovered

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AgentRegistry agents={self.list_agents()}>"


__all__ = ["AgentRegistry"]
