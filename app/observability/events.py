import asyncio
from typing import Callable, Dict, List


class EventEmitter:
    """Simple event bus for internal events."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable):
        self._handlers.setdefault(event, []).append(handler)

    async def emit(self, event: str, data: dict):
        for handler in self._handlers.get(event, []):
            await handler(data)