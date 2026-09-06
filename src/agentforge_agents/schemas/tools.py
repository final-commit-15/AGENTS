"""Tool schema and metadata schemas exposed by every registered tool."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolStatus(StrEnum):
    """Availability state of a tool at registration time."""

    READY = "ready"
    MISSING_CREDENTIALS = "missing_credentials"
    DISABLED = "disabled"
    ERROR = "error"


class ToolParameter(BaseModel):
    """A single declared parameter of a tool."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Any = None
    enum: list[str] | None = None


class ToolSchema(BaseModel):
    """Introspection schema describing how to call a tool."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)

    def json_schema(self) -> dict[str, Any]:
        """Convert to an OpenAI-function JSON schema style dictionary."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter in self.parameters:
            props: dict[str, Any] = {"type": parameter.type, "description": parameter.description}
            if parameter.enum:
                props["enum"] = parameter.enum
            if parameter.default is not None:
                props["default"] = parameter.default
            properties[parameter.name] = props
            if parameter.required:
                required.append(parameter.name)
        output: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            output["required"] = required
        return output


class ToolMetadata(BaseModel):
    """Static metadata returned by ``tool.metadata()``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = "1.0.0"
    description: str = ""
    category: str = "general"
    requires_credentials: bool = False
    credentials_present: bool = False
    status: ToolStatus = ToolStatus.READY
    tags: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=30.0, gt=0.0)


class ToolResult(BaseModel):
    """Outcome of executing a tool."""

    model_config = ConfigDict(extra="allow")

    tool_name: str
    success: bool = True
    output: Any = None
    error: str | None = None
    duration_ms: float = Field(default=0.0, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, tool_name: str, output: Any, **metadata: Any) -> ToolResult:
        return cls(tool_name=tool_name, success=True, output=output, metadata=metadata)

    @classmethod
    def err(cls, tool_name: str, error: str, **metadata: Any) -> ToolResult:
        return cls(tool_name=tool_name, success=False, error=error, metadata=metadata)


__all__ = [
    "ToolMetadata",
    "ToolParameter",
    "ToolResult",
    "ToolSchema",
    "ToolStatus",
]
