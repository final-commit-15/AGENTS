import pytest
from app.agents.base.agent import BaseAgent
from app.agents.base.config import AgentConfig
from app.agents.base.result import AgentResult


class DummyAgent(BaseAgent):
    async def execute(self, input_data):
        return AgentResult(agent_id=self.id, status="completed", output="done")


@pytest.mark.asyncio
async def test_agent_run():
    config = AgentConfig(name="dummy", id="dummy-1")
    agent = DummyAgent(config)
    result = await agent.run({"test": "input"})
    assert result.status == "completed"
    assert result.output == "done"