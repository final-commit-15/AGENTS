"""Git tool - status, log, diff, add, commit, clone on the local repository."""

from __future__ import annotations

import asyncio
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool

_OPERATIONS = {
    "status",
    "log",
    "diff",
    "add",
    "commit",
    "clone",
    "branch",
    "current_branch",
    "pull",
}


class GitTool(BaseTool):
    """Wrap common read-only and local git operations.

    Safe by construction: only the subcommands above run, with a timeout, and
    commits require an explicit message. No shell interpolation is used.
    """

    name = "git"
    description = (
        "Perform common git operations (status, log, diff, add, commit, clone, branch, pull)."
    )
    category = "vcs"
    timeout_seconds = 120.0
    tags = ["git", "vcs"]

    parameters = [
        ToolParameter(name="operation", type="string", required=True, enum=sorted(_OPERATIONS)),
        ToolParameter(
            name="repo",
            type="string",
            required=False,
            description="Repository path (defaults to cwd).",
        ),
        ToolParameter(
            name="message",
            type="string",
            required=False,
            description="Commit message (required for commit).",
        ),
        ToolParameter(
            name="url", type="string", required=False, description="Remote URL for clone."
        ),
        ToolParameter(
            name="path", type="string", required=False, description="Path filter for diff/add."
        ),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if arguments.get("operation") not in _OPERATIONS:
            errors.append("invalid operation")
        if arguments.get("operation") == "commit" and not arguments.get("message"):
            errors.append("commit requires a message")
        if arguments.get("operation") == "clone" and not arguments.get("url"):
            errors.append("clone requires a url")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        operation = str(arguments["operation"])
        repo = str(arguments.get("repo") or ".")
        args: list[list[str]] = []
        if operation == "status":
            args = [["status", "--short"], ["rev-parse", "--abbrev-ref", "HEAD"]]
        elif operation == "log":
            args = [["log", "--oneline", "-20"]]
        elif operation == "diff":
            args = (
                [["diff", "--stat"]]
                if not arguments.get("path")
                else [["diff", str(arguments["path"])]]
            )
        elif operation == "add":
            target = str(arguments.get("path") or ".")
            args = [["add", target]]
        elif operation == "commit":
            args = [["commit", "-m", str(arguments["message"])]]
        elif operation == "clone":
            args = [["clone", str(arguments["url"]), str(arguments.get("path") or "")]]
        elif operation == "branch":
            args = [["branch", "-a"]]
        elif operation == "current_branch":
            args = [["rev-parse", "--abbrev-ref", "HEAD"]]
        elif operation == "pull":
            args = [["pull", "--ff-only"]]

        outputs: list[dict[str, Any]] = []
        for argv in args:
            if not argv[1:]:
                continue
            result = await self._run_git(repo, argv)
            outputs.append(result)
        if not outputs:
            return self.err("no operation ran")
        all_ok = all(out["ok"] for out in outputs)
        combined = "\n".join(out["output"] for out in outputs if out["output"])
        return self.ok(
            {"results": outputs, "combined": combined},
            succeeded=all_ok,
        )

    async def _run_git(self, repo: str, argv: list[str]) -> dict[str, Any]:
        process = await asyncio.create_subprocess_exec(
            "git",
            *argv,
            cwd=repo,
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
            return {"ok": False, "output": "git timed out", "exit_code": -1}
        text = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
        return {
            "ok": process.returncode == 0,
            "output": text[:4000],
            "exit_code": process.returncode,
        }


__all__ = ["GitTool"]
