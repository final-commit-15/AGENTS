"""Built-in agent catalogue.

Each subpackage exposes a config-driven ``Agent`` class. The registry and the
config loader enumerate these statically, so adding an agent only requires a
new subpackage (plus its ``config.yaml``).

The canonical catalogue lives in ``config/configs/agents.yaml``.
"""

from __future__ import annotations

from agentforge_agents.agents.automation.agent import Agent as AutomationAgent
from agentforge_agents.agents.browser.agent import Agent as BrowserAgent
from agentforge_agents.agents.coding.agent import Agent as CodingAgent
from agentforge_agents.agents.communication.agent import Agent as CommunicationAgent
from agentforge_agents.agents.data.agent import Agent as DataAgent
from agentforge_agents.agents.document.agent import Agent as DocumentAgent
from agentforge_agents.agents.memory.agent import Agent as MemoryAgent
from agentforge_agents.agents.planner.agent import Agent as PlannerAgent
from agentforge_agents.agents.research.agent import Agent as ResearchAgent
from agentforge_agents.agents.workflow.agent import Agent as WorkflowAgent

AGENT_CLASSES: dict[str, type] = {
    "planner": PlannerAgent,
    "coding": CodingAgent,
    "research": ResearchAgent,
    "data": DataAgent,
    "automation": AutomationAgent,
    "browser": BrowserAgent,
    "document": DocumentAgent,
    "memory": MemoryAgent,
    "workflow": WorkflowAgent,
    "communication": CommunicationAgent,
}

AGENT_PROMPTS: dict[str, str] = {}


def load_prompt(agent_id: str) -> str:
    """Load the packaged system prompt for an agent (cached in module state)."""
    if not AGENT_PROMPTS:
        from importlib import resources

        import agentforge_agents.agents as agents_pkg

        for package in (
            "planner",
            "coding",
            "research",
            "data",
            "automation",
            "browser",
            "document",
            "memory",
            "workflow",
            "communication",
        ):
            try:
                text = (
                    resources.files(f"{agents_pkg.__name__}.{package}")
                    .joinpath("prompt.md")
                    .read_text(encoding="utf-8")
                )
            except (FileNotFoundError, OSError, TypeError):
                continue
            AGENT_PROMPTS[package] = text
    return AGENT_PROMPTS.get(agent_id, "")


__all__ = ["AGENT_CLASSES", "AGENT_PROMPTS", "load_prompt"]
