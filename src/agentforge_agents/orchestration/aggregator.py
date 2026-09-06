"""Response aggregation and delegation helpers for orchestrations."""

from __future__ import annotations

import json
from typing import Any

from agentforge_agents.schemas.task import TaskResult
from agentforge_agents.utils.serialization import to_json


class ResponseAggregator:
    """Merges multiple agent results into a coherent composite.

    ``merge_mode`` controls how each result's ``output`` is folded:

    * ``concat`` - join string outputs with a separator
    * ``json`` - combine outputs into a JSON object keyed by task id
    * ``list`` - flatten outputs into a list
    * ``summary`` - keep a compact summary per task (safe for any output type)
    """

    def __init__(self, *, merge_mode: str = "summary", separator: str = "\n\n") -> None:
        if merge_mode not in {"concat", "json", "list", "summary"}:
            raise ValueError(f"unknown merge mode: {merge_mode}")
        self.merge_mode = merge_mode
        self.separator = separator

    def merge(self, results: list[TaskResult]) -> dict[str, Any]:
        ordered = sorted(results, key=lambda r: r.task_id)
        if self.merge_mode == "concat":
            return {
                "combined": self.separator.join(_to_text(r.output) for r in ordered),
                "count": len(ordered),
            }
        if self.merge_mode == "json":
            return {r.task_id: r.output for r in ordered}
        if self.merge_mode == "list":
            return {"items": [r.output for r in ordered], "count": len(ordered)}
        return {
            "summary": [
                {
                    "task_id": r.task_id,
                    "agent": r.agent_id,
                    "status": r.status.value,
                    "output": _to_text(r.output)[:500],
                }
                for r in ordered
            ],
            "count": len(ordered),
        }

    @staticmethod
    def to_pretty_json(results: list[TaskResult]) -> str:
        return to_json(
            [
                {
                    "task_id": r.task_id,
                    "agent": r.agent_id,
                    "status": r.status.value,
                    "output": r.output,
                }
                for r in results
            ],
            pretty=True,
        )


class DelegationManager:
    """Tracks cross-agent delegation and resolves values across namespaces.

    Delegated tasks write their outputs under the parent session so downstream
    agents can read them; see :meth:`resolve_input` for ``{{ delegates.X }}``.
    """

    def __init__(self) -> None:
        self._outputs: dict[str, Any] = {}

    def register_output(self, task_id: str, output: Any) -> None:
        self._outputs[task_id] = output

    def get_output(self, task_id: str) -> Any:
        return self._outputs.get(task_id)

    def resolve_input(self, template: Any) -> Any:
        """Resolve ``{"$delegate": "task_id"}`` references in a template dict."""
        if isinstance(template, dict):
            if set(template) == {"$delegate"}:
                return self._outputs.get(str(template["$delegate"]))
            return {key: self.resolve_input(value) for key, value in template.items()}
        if isinstance(template, list):
            return [self.resolve_input(item) for item in template]
        if isinstance(template, str) and template.startswith("{{"):
            key = template.strip("{} ").strip()
            if key in self._outputs:
                output = self._outputs[key]
                if isinstance(output, (dict, list)):
                    return json.dumps(output)
                return str(output)
        return template


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        try:
            return to_json(value)
        except TypeError:
            return str(value)
    return str(value)


__all__ = ["DelegationManager", "ResponseAggregator"]
