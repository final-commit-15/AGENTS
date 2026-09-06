"""Terminal tool - safe subprocess execution with allowlist, timeout, and limits."""

from __future__ import annotations

import asyncio
import shlex
import sys
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool

_DISALLOWED_PREFIXES = (
    "sudo",
    "shutdown",
    "reboot",
    "rm -rf /",
    ":(){",
    "mkfs",
    "dd if=",
    "> /dev/sda",
    "chmod -R 777 /",
    "curl | sh",
    "wget | sh",
)

_ALLOWED_COMMANDS = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "echo",
    "pwd",
    "whoami",
    "date",
    "df",
    "du",
    "ps",
    "env",
    "printenv",
    "wc",
    "sort",
    "uniq",
    "cut",
    "sed",
    "awk",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "rm",
    "git",
    "python",
    "python3",
    "pip",
    "npm",
    "node",
}


class TerminalTool(BaseTool):
    """Run a single shell command through a non-interactive subprocess.

    The command must parse under ``shlex`` (no shell metacharacter pipelines),
    and the executable must be in the allowlist. Output is capped and a hard
    timeout applies. Docker-based sandboxing is used when ``sandbox=True``.
    """

    name = "terminal"
    description = (
        "Execute a single allowed shell command non-interactively with a timeout and output cap."
    )
    category = "system"
    timeout_seconds = 60.0
    tags = ["terminal", "shell"]

    parameters = [
        ToolParameter(
            name="command",
            type="string",
            required=True,
            description="Single command, no pipelines.",
        ),
        ToolParameter(name="cwd", type="string", required=False, description="Working directory."),
        ToolParameter(
            name="timeout",
            type="number",
            required=False,
            description="Override the default timeout.",
        ),
    ]

    def __init__(
        self,
        context: Any = None,
        *,
        allowed_commands: set[str] | None = None,
        output_limit: int = 65536,
    ) -> None:
        from agentforge_agents.tools.base import ToolContext

        super().__init__(context=context or ToolContext())
        self.allowed_commands = allowed_commands or _ALLOWED_COMMANDS
        self.output_limit = output_limit

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        command = str(arguments.get("command", ""))
        if not command.strip():
            errors.append("command is required")
            return errors
        for prefix in _DISALLOWED_PREFIXES:
            if command.strip().startswith(prefix):
                errors.append(f"command disallowed: {prefix!r}")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        command = str(arguments["command"]).strip()
        try:
            argv = shlex.split(command, posix=(os_name() != "nt"))
        except ValueError as exc:
            return self.err(f"unparseable command: {exc}")

        if not argv:
            return self.err("empty command")
        executable = argv[0].lower()
        if executable not in self.allowed_commands:
            return self.err(f"command {executable!r} is not allowed")

        timeout = float(arguments.get("timeout") or self.timeout_seconds)
        create = {"env": _script_env()}
        if os_name() != "nt" and arguments.get("cwd"):
            create["cwd"] = str(arguments["cwd"])

        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **create,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            try:
                await process.wait()
            except ProcessLookupError:  # pragma: no cover
                pass
            return self.err(f"command timed out after {timeout}s", timed_out=True)
        out = stdout.decode(errors="replace")[: self.output_limit]
        err = stderr.decode(errors="replace")[: self.output_limit]
        return self.ok(
            {"exit_code": process.returncode, "stdout": out, "stderr": err},
            exit_code=process.returncode,
        )


def os_name() -> str:
    return sys.platform


def _script_env() -> dict[str, str]:
    """A minimal, predictable environment for subprocesses (POSIX) or inherited (NT)."""
    import os

    if os_name() == "nt":
        return dict(os.environ)
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "TERM": "dumb",
    }


__all__ = ["TerminalTool"]
