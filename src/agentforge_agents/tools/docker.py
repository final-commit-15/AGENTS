"""Docker tool - build, run, stop, and inspect containers via the Docker CLI."""

from __future__ import annotations

import asyncio
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool

_OPERATIONS = {"build", "run", "stop", "ps", "images", "pull", "logs", "rm"}


class DockerTool(BaseTool):
    """Execute Docker CLI operations.

    Requires the docker CLI to be available on the host. Each operation maps to
    a single, non-shell-interpolated ``docker`` invocation with a timeout.
    """

    name = "docker"
    description = "Build, run, stop, pull, inspect Docker images and containers."
    category = "system"
    timeout_seconds = 300.0
    tags = ["docker", "containers"]

    parameters = [
        ToolParameter(name="operation", type="string", required=True, enum=sorted(_OPERATIONS)),
        ToolParameter(name="image", type="string", required=False, description="Image reference."),
        ToolParameter(
            name="container", type="string", required=False, description="Container name / id."
        ),
        ToolParameter(name="tag", type="string", required=False, description="Tag for build."),
        ToolParameter(
            name="context", type="string", required=False, description="Build context path."
        ),
        ToolParameter(
            name="command",
            type="string",
            required=False,
            description="Command to run inside the container.",
        ),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if arguments.get("operation") not in _OPERATIONS:
            errors.append("invalid operation")
        if arguments.get("operation") == "build" and not (
            arguments.get("context") and arguments.get("image")
        ):
            errors.append("build requires context and image")
        if arguments.get("operation") == "run" and not arguments.get("image"):
            errors.append("run requires an image")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        operation = str(arguments["operation"])
        argv = self._build_argv(operation, arguments)
        process = await asyncio.create_subprocess_exec(
            "docker",
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return self.err(f"docker {operation} timed out", timed_out=True)
        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        return self.ok(
            {"exit_code": process.returncode, "stdout": out[:8000], "stderr": err[:4000]},
            exit_code=process.returncode,
        )

    def _build_argv(self, operation: str, args: dict[str, Any]) -> list[str]:
        if operation == "build":
            argv = ["build", "-t", str(args["image"])]
            if args.get("tag"):
                argv += ["--tag", f"{args['image']}:{args['tag']}"]
            argv.append(str(args["context"]))
            return argv
        if operation == "run":
            argv = ["run", "--rm", "-d"]
            if args.get("command"):
                argv.append(str(args["command"]))
            argv.append(str(args["image"]))
            return argv
        if operation == "stop":
            return ["stop", str(args.get("container") or args.get("image") or "")]
        if operation == "ps":
            return ["ps", "-a"]
        if operation == "images":
            return ["images"]
        if operation == "pull":
            return ["pull", str(args.get("image") or "")]
        if operation == "logs":
            target = str(args.get("container") or args.get("image") or "")
            return ["logs", "--tail", "200", target]
        if operation == "rm":
            return ["rm", "-f", str(args.get("container") or "")]
        return [operation]


__all__ = ["DockerTool"]
