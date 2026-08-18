from app.agents.memory.short_term import ShortTermMemory


class ContextManager:
    """Orchestrates context for multi-agent workflows."""

    def __init__(self):
        self.global_context = ShortTermMemory()

    def get_agent_context(self, agent_id: str) -> ShortTermMemory:
        # Could create a scoped memory per agent
        return self.global_context