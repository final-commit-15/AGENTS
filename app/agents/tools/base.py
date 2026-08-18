"""
Base abstractions for tools in AgentForge.

Tools are reusable capabilities that agents can invoke.
Each tool defines its input/output schemas and execution logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base class for all tool input schemas."""
    pass


class ToolOutput(BaseModel):
    """Standard output structure for all tools."""
    result: Any
    metadata: Dict[str, Any] = {}


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Attributes:
        name: Unique identifier for the tool.
        description: Human-readable description.
        input_schema: Pydantic model class for validating inputs.
        output_schema: Pydantic model class for outputs (optional).
    """
    name: str
    description: str
    input_schema: type[ToolInput] = ToolInput
    output_schema: type[ToolOutput] = ToolOutput

    @abstractmethod
    async def execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Execute the tool with validated input.

        Args:
            input_data: An instance of the input_schema class.

        Returns:
            ToolOutput containing the result and metadata.
        """
        pass