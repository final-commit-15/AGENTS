"""Agent router - resolves which agent handles a task request."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from typing import Any

from agentforge_agents.core.registry import AgentRegistry
from agentforge_agents.schemas.task import TaskRequest
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class RoutingRule:
    """A keyword/capability rule mapping tasks to agents."""

    agent_id: str
    keywords: tuple[str, ...] = ()
    description: str = ""

    def matches(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.keywords)


_DEFAULT_RULES = [
    RoutingRule("planner", ("plan", "organize", "break down", "strategy", "decompose")),
    RoutingRule(
        "coding", ("code", "python", "typescript", "bug", "refactor", "function", "api", "software")
    ),
    RoutingRule("research", ("research", "search", "summarize sources", "citations", "find out")),
    RoutingRule("data", ("sql", "data", "pandas", "statistics", "dataset", "analysis", "csv")),
    RoutingRule("document", ("pdf", "docx", "report document", "memo", "spreadsheet", "pptx")),
    RoutingRule("automation", ("automate", "schedule", "workflow sync", "integration")),
    RoutingRule("communication", ("email", "slack message", "notification", "meeting", "teams")),
    RoutingRule("memory", ("remember", "recall", "memory", "forget")),
    RoutingRule("browser", ("website", "web page", "browser", "form", "screenshot")),
]


class AgentRouter:
    """Keyword heuristic router with explicit override support.

    ``agent_id`` in the request's ``context``/``input`` always wins; otherwise
    the first matching rule route is returned; finally ``default`` is used.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        rules: list[RoutingRule] | None = None,
        *,
        default_agent: str = "planner",
    ) -> None:
        self.registry = registry
        self.rules = rules or list(_DEFAULT_RULES)
        self.default_agent = default_agent

    def route_request(self, request: TaskRequest) -> str:
        """Return the agent id for ``request``."""
        explicit = (
            request.input.get("agent_id")
            or request.context.get("agent_id")
            or (request.metadata.get("agent_id") if request.metadata else None)
        )
        if explicit:
            return str(explicit)
        text = " ".join(
            filter(
                None,
                [request.instructions, str(request.input), request.context.get("instructions", "")],
            )
        )
        text = textwrap.dedent(text)
        return self.route_text(text)

    def route_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").lower())
        for rule in self.rules:
            if any(keyword in normalized for keyword in rule.keywords):
                candidate = rule.agent_id
                if self.registry is None or self.registry.has(candidate):
                    return candidate
        if self.registry is None:
            return self.default_agent
        if self.registry.has(self.default_agent):
            return self.default_agent
        enabled = self.registry.enabled_ids()
        return enabled[0] if enabled else self.default_agent

    def describe(self) -> dict[str, Any]:
        return {
            "default_agent": self.default_agent,
            "rules": [
                {"agent_id": rule.agent_id, "keywords": list(rule.keywords)} for rule in self.rules
            ],
        }


__all__ = ["AgentRouter", "RoutingRule"]
