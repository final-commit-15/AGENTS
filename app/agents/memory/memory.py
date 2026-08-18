from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Memory(ABC):
    """Interface for long-term memory storage."""

    @abstractmethod
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None):
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass