"""Checkpoint manager - persist and resume workflow/orchestrator state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentforge_agents.utils.errors import AgentForgeError
from agentforge_agents.utils.serialization import from_json, to_json
from agentforge_agents.utils.time import utc_now


class CheckpointManager:
    """Filesystem-backed JSON checkpoints keyed by run id.

    Snapshots are atomic (write-temp-then-rename) and timestamped, so a crashed
    orchestrator can resume from the most recent checkpoint.
    """

    def __init__(self, directory: str | Path = "checkpoints") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.directory / f"{run_id}.json"

    async def save(self, run_id: str, state: dict[str, Any]) -> Path:
        """Persist ``state`` for ``run_id``; returns the checkpoint path."""
        timestamped = {"checkpointed_at": utc_now().isoformat(), "state": state}
        target = self._path(run_id)
        temp_target = target.with_suffix(".tmp")
        temp_target.write_text(to_json(timestamped), encoding="utf-8")
        temp_target.replace(target)
        return target

    async def load(self, run_id: str) -> dict[str, Any] | None:
        """Read the latest checkpoint for ``run_id`` or None."""
        target = self._path(run_id)
        if not target.is_file():
            return None
        try:
            data = from_json(target.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AgentForgeError(f"corrupt checkpoint {target}: {exc}") from exc
        return data.get("state")

    async def exists(self, run_id: str) -> bool:
        return self._path(run_id).is_file()

    async def delete(self, run_id: str) -> bool:
        target = self._path(run_id)
        if target.is_file():
            target.unlink()
            return True
        return False

    async def list_runs(self) -> list[str]:
        return [path.stem for path in sorted(self.directory.glob("*.json"))]


__all__ = ["CheckpointManager"]
