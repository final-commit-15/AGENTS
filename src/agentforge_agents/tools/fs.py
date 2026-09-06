"""Filesystem tool - safe, path-constrained read/write operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool
from agentforge_agents.utils.errors import ToolError

_ALLOWED_OPERATIONS = {"read", "write", "list", "exists", "delete", "stat", "mkdir"}


class FilesystemTool(BaseTool):
    """Read, write, list, stat, and delete files below a configurable root."""

    name = "filesystem"
    description = (
        "Read, write, list, stat, mkdir, and delete files within an allowed root directory."
    )
    category = "system"
    tags = ["filesystem", "io"]

    parameters = [
        ToolParameter(
            name="operation", type="string", required=True, enum=sorted(_ALLOWED_OPERATIONS)
        ),
        ToolParameter(
            name="path",
            type="string",
            required=True,
            description="Path relative to the configured root.",
        ),
        ToolParameter(
            name="content",
            type="string",
            required=False,
            description="Content for write operations.",
        ),
    ]

    def __init__(self, context: Any = None, *, root: str | None = None) -> None:
        from agentforge_agents.tools.base import ToolContext

        super().__init__(context=context or ToolContext())
        self.root = Path(root or os.environ.get("AGENTFORGE_TOOL_ROOT", ".")).resolve()

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if arguments.get("operation") not in _ALLOWED_OPERATIONS:
            errors.append("invalid operation")
        if not arguments.get("path"):
            errors.append("path is required")
        return errors

    def _resolve(self, arguments: dict[str, Any]) -> Path:
        raw = str(arguments["path"])
        target = (self.root / raw).resolve()
        if not (target == self.root or self.root in target.parents):
            raise ToolError("path escapes the allowed root", tool_name=self.name)
        return target

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        operation = arguments["operation"]
        path = self._resolve(arguments)
        try:
            if operation == "read":
                if not path.is_file():
                    return self.err("file not found")
                return self.ok({"path": str(path), "content": path.read_text(encoding="utf-8")})
            if operation == "write":
                parent = path.parent
                parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(arguments.get("content", "")), encoding="utf-8")
                return self.ok({"path": str(path), "written": True, "bytes": path.stat().st_size})
            if operation == "list":
                if not path.is_dir():
                    return self.err("not a directory")
                entries = [
                    {
                        "name": p.name,
                        "dir": p.is_dir(),
                        "size": p.stat().st_size if p.is_file() else 0,
                    }
                    for p in sorted(path.iterdir())
                ]
                return self.ok({"path": str(path), "entries": entries, "count": len(entries)})
            if operation == "exists":
                return self.ok({"path": str(path), "exists": path.exists()})
            if operation == "stat":
                if not path.exists():
                    return self.err("path does not exist")
                stat = path.stat()
                return self.ok(
                    {
                        "path": str(path),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "dir": path.is_dir(),
                    }
                )
            if operation == "mkdir":
                path.mkdir(parents=True, exist_ok=True)
                return self.ok({"path": str(path), "created": True})
            if operation == "delete":
                if not path.exists():
                    return self.err("path does not exist")
                if path.is_dir():
                    path.rmdir()
                else:
                    path.unlink()
                return self.ok({"path": str(path), "deleted": True})
        except OSError as exc:
            return self.err(f"{operation} failed: {exc}")
        raise ToolError("unreachable", tool_name=self.name)


__all__ = ["FilesystemTool"]
