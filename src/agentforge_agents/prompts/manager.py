"""PromptManager - load, version, and render the prompt library.

Prompts live as Markdown package data under ``prompts/system``,
``prompts/templates``, and ``prompts/guardrails`` and are declared in a
``manifest.yaml`` that pins versions. Managers can be pointed at a filesystem
override directory so operators can hot-edit production prompts.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any

from jinja2 import Template

from agentforge_agents.utils.errors import ConfigError
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)

_PACKAGE = "agentforge_agents.prompts"
_MANIFEST = "manifest.yaml"


class PromptManager:
    """Resolves prompt names to versioned, renderable Markdown text."""

    def __init__(self, *, override_dir: str | Path | None = None) -> None:
        self.override_dir = Path(override_dir) if override_dir else None
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, dict[str, Any]]:
        source = self.override_dir
        try:
            text = (
                (source / _MANIFEST).read_text(encoding="utf-8")
                if source and (source / _MANIFEST).is_file()
                else (importlib.resources.files(_PACKAGE) / _MANIFEST).read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            return {}
        import yaml

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ConfigError("prompt manifest must be a mapping")
        return {str(name): dict(entry) for name, entry in data.items()}

    # ------------------------------------------------------------ resolve
    def resolve_path(self, name: str) -> tuple[Path, dict[str, Any]]:
        """Return ``(path, entry)`` for a prompt ``name`` (system/template/guardrail)."""
        entry = self._manifest.get(name)
        if entry is None:
            raise ConfigError(f"unknown prompt: {name!r}")
        relative = entry.get("path")
        if not relative:
            raise ConfigError(f"prompt {name!r} has no path")
        if self.override_dir is not None:
            candidate = self.override_dir / relative
            if candidate.is_file():
                return candidate, entry
        return (
            Path(str(importlib.resources.files(_PACKAGE) / relative)),
            entry,
        )

    def version_of(self, name: str) -> str:
        entry = self._manifest.get(name)
        return str(entry.get("version", "1.0.0")) if entry else "unknown"

    def has(self, name: str) -> bool:
        return name in self._manifest

    def names(self) -> list[str]:
        return sorted(self._manifest)

    # ------------------------------------------------------------- loading
    def load(self, name: str) -> str:
        path, _ = self.resolve_path(name)
        return path.read_text(encoding="utf-8")

    def load_strict(self, name: str) -> str:
        """Load a prompt, requiring it to be non-empty."""
        content = self.load(name)
        if not content.strip():
            raise ConfigError(f"prompt {name!r} resolved empty")
        return content

    def render(self, name: str, **context: Any) -> str:
        """Render a prompt template with Jinja2 variables."""
        content = self.load(name)
        try:
            return Template(content).render(**context)
        except Exception as exc:
            raise ConfigError(f"prompt render failed for {name!r}: {exc}") from exc

    # ---------------------------------------------------------- aggregators
    def system_prompt(self, agent_id: str) -> str:
        """The packaged system prompt for an agent package."""
        package = f"{_PACKAGE}.system"
        try:
            text = (importlib.resources.files(package) / f"{agent_id}.md").read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            raise ConfigError(f"no system prompt for agent {agent_id!r}") from None
        return text

    def guardrails_for(self, agent_id: str) -> str:
        """Concatenate applicable guardrails (default set + optional agent-specific)."""
        sections: list[str] = []
        for guardrail in ("safety", "hallucination", "permission"):
            try:
                text = (
                    importlib.resources.files(f"{_PACKAGE}.guardrails") / f"{guardrail}.md"
                ).read_text(encoding="utf-8")
                sections.append(f"## Guardrail: {guardrail}\n\n{text}")
            except FileNotFoundError:
                continue
        try:
            custom = (
                importlib.resources.files(f"{_PACKAGE}.guardrails") / f"{agent_id}.md"
            ).read_text(encoding="utf-8")
            sections.append(f"## Guardrail: {agent_id}\n\n{custom}")
        except FileNotFoundError:
            pass
        return "\n\n".join(sections)

    def agents_available(self) -> list[str]:
        """List system prompts available (i.e. registered agent ids)."""
        return [
            path.stem
            for path in (importlib.resources.files(f"{_PACKAGE}.system")).iterdir()  # type: ignore[union-attr]
            if path.suffix == ".md"
        ]


__all__ = ["PromptManager"]
