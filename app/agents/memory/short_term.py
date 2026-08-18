from typing import Dict, Any, List


class ShortTermMemory:
    """
    Manages the current execution context, including conversation,
    intermediate results, and state.
    """

    def __init__(self):
        self.conversation: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {}
        self.previous_results: Dict[str, Any] = {}

    def add_message(self, role: str, content: str):
        self.conversation.append({"role": role, "content": content})

    def get_context_window(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        return self.conversation[-max_messages:]

    def update_state(self, key: str, value: Any):
        self.state[key] = value

    def get_state(self, key: str, default=None):
        return self.state.get(key, default)