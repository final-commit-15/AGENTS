"""Docker runner - containerised execution with resource and network controls."""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

from agentforge_agents.execution.base import ExecutionTarget, RunResult
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)


class DockerRunner(ExecutionTarget):
    """Run code inside a disposable container.

    Requires the ``docker`` CLI. The image defaults to ``python:3.12-slim`` and
    the network defaults to ``none`` unless explicitly overridden - the safest
    default for untrusted payloads.
    """

    def __init__(
        self,
        *,
        image: str | None = None,
        timeout_seconds: float = 120.0,
        memory_limit: str = "512m",
        network: str | None = None,
        enable_network: bool = False,
        volumes: dict[str, str] | None = None,
    ) -> None:
        self.image = image or os.environ.get("AGENTFORGE_DOCKER_IMAGE", "python:3.12-slim")
        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        # net=host is mapped to the docker "host" network; default "none" is safest.
        self.network = network or ("host" if enable_network and os.name == "posix" else "none")
        self.volumes = volumes or {}

    # ------------------------------------------------------------ interface
    async def run_code(
        self,
        code: str | list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        interpreter: str | None = None,
    ) -> dict[str, Any]:
        command = code if isinstance(code, list) else [(interpreter or "python"), "-c", code]
        return await self.run_cmd(command, env=env)

    async def run_cmd(
        self, command: list[str] | str, *, env: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Run a command in a fresh container and return the raw result."""
        with tempfile.TemporaryDirectory(prefix="agentforge-docker-") as tmp:
            return await self._run_container(str(tmp), command, env or {})

    async def _run_container(
        self, workdir: str, command: list[str] | str, env: dict[str, str]
    ) -> dict[str, Any]:
        argv_command = command if isinstance(command, list) else ["sh", "-c", command]
        argv = [
            "docker",
            "run",
            "--rm",
            "--network",
            self.network,
            "--memory",
            self.memory_limit,
            "--pids-limit",
            "64",
            "--read-only",
            "-v",
            f"{workdir}:/workspace",
            "-w",
            "/workspace",
        ]
        for key, value in _sanitised_env(env).items():
            argv += ["-e", f"{key}={value}"]
        argv.append(self.image)
        argv += argv_command

        process = await asyncio.create_subprocess_exec(
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
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"docker execution timed out after {self.timeout_seconds}s",
                "timed_out": True,
            }
        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "timed_out": False,
        }

    async def run(self, command: list[str] | str, *, workdir_file: str | None = None) -> RunResult:
        result = await self.run_cmd(command)
        return RunResult(
            success=result["exit_code"] == 0 and not result.get("timed_out"),
            output={"stdout": result["stdout"], "stderr": result["stderr"]},
            error=result["stderr"] or ("timed out" if result.get("timed_out") else None),
            metadata=result,
        )

    async def image_exists(self) -> bool:
        process = await asyncio.create_subprocess_exec(
            "docker",
            "image",
            "inspect",
            self.image,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return await process.wait() == 0

    async def close(self) -> None:
        pass


def _sanitised_env(env: dict[str, str]) -> dict[str, str]:
    return {
        str(k): str(v)
        for k, v in env.items()
        if not k.upper().endswith("_KEY") and "SECRET" not in k.upper()
    }


__all__ = ["DockerRunner"]
