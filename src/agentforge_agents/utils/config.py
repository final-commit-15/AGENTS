"""Configuration loader translating YAML files plus env overrides into Pydantic models."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from agentforge_agents.utils.errors import ConfigError
from agentforge_agents.utils.serialization import to_dict

T = TypeVar("T", bound=BaseModel)

_ENV_OVERRIDE_PREFIX = "AGENTFORGE_"


def read_yaml(path: str | Path) -> dict[str, Any]:
    """Read and parse a YAML file; raises :class:`ConfigError` on failure."""
    file_path = Path(path)
    if not file_path.is_file():
        raise ConfigError(f"config file not found: {file_path}")
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigError(f"malformed YAML in {file_path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"config root must be a mapping: {file_path}")
    return data


def load_model[model_cls: type[BaseModel]](
    model_cls: model_cls, path: str | Path, *, env_override: bool = True
) -> model_cls:
    """Load a YAML file into ``model_cls`` with optional env overrides."""
    raw = read_yaml(path)
    if env_override:
        raw = _apply_env_overrides(raw, prefix=_ENV_OVERRIDE_PREFIX)
    try:
        return model_cls(**raw)
    except Exception as exc:
        raise ConfigError(f"invalid config for {model_cls.__name__} from {path}: {exc}") from exc


def apply_env_overrides[model: BaseModel](
    model: model, *, prefix: str = _ENV_OVERRIDE_PREFIX
) -> model:
    """Return a deep-copied model with any matching env vars applied.

    Env key ``{PREFIX}{SECTION}__{FIELD}`` (e.g. ``AGENTFORGE_LOGGING__LEVEL``)
    drives nested overrides; a bare scalar override uses the field name.
    """
    data = to_dict(model)
    data = _apply_env_overrides(data, prefix=prefix)
    try:
        return model.__class__(**data)  # type: ignore[arg-type]
    except Exception as exc:
        raise ConfigError(
            f"env override produced an invalid {model.__class__.__name__}: {exc}"
        ) from exc


def _apply_env_overrides(data: dict[str, Any], *, prefix: str) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        stripped = key[len(prefix) :].strip("_")
        if not stripped:
            continue
        if "_" not in stripped and stripped in data and isinstance(data[stripped], dict):
            # Map pseudo-nested flat config (LOGGING__LEVEL) is handled below; a
            # bare key whose target is a mapping is ignored to avoid corruption.
            continue
        flattened[stripped] = value
    for key, value in flattened.items():
        if "__" in key:
            section, field = key.split("__", 1)
            if section in data and isinstance(data[section], dict):
                data[section][field] = _coerce_scalar(value)
            continue
        if key in data and not isinstance(data[key], dict):
            data[key] = _coerce_scalar(value)
    return data


def _coerce_scalar(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "1"}:
        return True
    if lowered in {"false", "no", "0"}:
        return False
    if lowered in {"none", "null", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


__all__ = ["apply_env_overrides", "load_model", "read_yaml"]
