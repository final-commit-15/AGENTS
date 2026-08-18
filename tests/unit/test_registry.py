from app.agents.registry.registry import AgentRegistry
from app.agents.base.config import AgentConfig
from tests.unit.test_agent import DummyAgent


def test_registry():
    registry = AgentRegistry()
    config = AgentConfig(name="dummy", id="dummy-1")
    registry.register(DummyAgent, config)
    assert "dummy-1" in registry.list_agents()
    cls = registry.get_agent_class("dummy-1")
    assert cls == DummyAgent