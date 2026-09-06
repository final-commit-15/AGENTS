"""Python runner tool - executes code snippets in an isolated scope."""

from __future__ import annotations

import contextlib
import io
import traceback
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool


class PythonRunnerTool(BaseTool):
    """Run a Python snippet with a cleaned local namespace.

    Execution is synchronous and blocking; prefer the Docker runner for
    untrusted code. The snippet sees no local file-state and captures stdout.
    """

    name = "python_runner"
    description = (
        "Evaluate a Python snippet, returning its stdout, locals summary, and any error trace."
    )
    category = "system"
    timeout_seconds = 30.0
    tags = ["python"]

    parameters = [
        ToolParameter(
            name="code", type="string", required=True, description="Python source to execute."
        ),
        ToolParameter(
            name="timeout",
            type="number",
            required=False,
            description="Override the default timeout.",
        ),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        if not arguments.get("code") or not str(arguments["code"]).strip():
            return ["code is required"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        code = str(arguments["code"])
        output = io.StringIO()
        namespace: dict[str, Any] = {"__name__": "__agent__"}
        try:
            with contextlib.redirect_stdout(output):
                exec(compile(code, "<agent-code>", "exec"), namespace)
            safe_locals = {k: str(v)[:200] for k, v in namespace.items() if not k.startswith("__")}
            return self.ok(
                {
                    "stdout": output.getvalue(),
                    "locals": safe_locals,
                    "locals_keys": sorted(safe_locals),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return self.err(
                f"execution failed: {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}"
            )


__all__ = ["PythonRunnerTool"]
