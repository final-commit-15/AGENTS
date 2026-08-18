"""
Central registry for all tools.

Allows agents to discover and invoke tools by name.
"""

from typing import Dict, Type, List, Optional
from .base import BaseTool


class ToolRegistry:
    """
    Singleton registry that holds all available tool classes.

    Provides methods to register, retrieve, and list tools.
    """
    _instance = None
    _tools: Dict[str, Type[BaseTool]]   # class‑level annotation

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}    # assign without annotation
        return cls._instance

    def register(self, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class.

        Args:
            tool_class: A subclass of BaseTool.
        """
        self._tools[tool_class.name] = tool_class

    def get(self, name: str) -> Type[BaseTool]:
        """
        Retrieve a tool class by name.

        Args:
            name: The tool's unique name.

        Returns:
            The tool class.

        Raises:
            KeyError: If the tool is not registered.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def list_tools(self) -> List[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())

    def get_all(self) -> Dict[str, Type[BaseTool]]:
        """Return a copy of the internal tool dictionary."""
        return self._tools.copy()