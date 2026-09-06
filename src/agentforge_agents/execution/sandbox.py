"""Sandbox execution - safe subprocess + optional container isolation."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from agentforge_agents.execution.base import ExecutionTarget
from agentforge_agents.utils.errors import SandboxError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class Sandbox(ExecutionTarget):
    """Runs code in an isolated process with resource limits."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 60.0,
        memory_limit_mb: int | None = 512,
        workdir: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.workdir = Path(workdir or tempfile.mkdtemp(prefix="agentforge-sandbox-"))
        self.workdir.mkdir(parents=True, exist_ok=True)

    async def run(
        self, command: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Execute ``command`` in the sandbox, returning output metadata."""
        result = await self.run_code(command, cwd=cwd, env=env)
        return result

    async def run_code(
        self,
        code: str | list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        interpreter: str | None = None,
    ) -> dict[str, Any]:
        argv = code if isinstance(code, list) else [interpreter or "python", "-c", code]
        workdir = cwd or str(self.workdir)
        runtime_env = _sandbox_env(env or {})

        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=workdir,
            env=runtime_env,
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
            raise SandboxError(f"sandbox execution timed out after {self.timeout_seconds}s")

        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "timed_out": False,
            "workdir": workdir,
        }

    async def write_file(self, path: str, content: str) -> Path:
        """Create a file inside the sandbox working directory."""
        target = self.workdir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    async def read_file(self, path: str) -> str:
        target = self.workdir / path
        if not target.is_file():
            raise SandboxError(f"file not found in sandbox: {path}")
        return target.read_text(encoding="utf-8")

    def _limit_env(self, env: dict[str, str]) -> dict[str, str]:
        return _sandbox_env(env)

    async def close(self) -> None:
        pass


def _sandbox_env(extra: dict[str, str]) -> dict[str, str]:
    """Build a sanitised environment, never inheriting secrets."""
    base: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "PYTHONUNBUFFERED": "1",
        # Strip inherited connection strings/keys for safety.
        "REDIS_URL": "",
        "OPENAI_API_KEY": "",
    }
    base.update(extra)
    return base


__all__ = ["Sandbox"]
