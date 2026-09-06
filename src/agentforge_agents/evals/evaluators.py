"""Evaluators that judge an agent's output against expected content."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentforge_agents.evals.schemas import EvalOutcome

ALLOWED_KEYWORDS = {
    "analysis",
    "paragraph",
    "summary",
    "mock",
    "report",
    "explain",
    "workflow",
    "experiment",
}


class BaseEvaluator(ABC):
    """Base class for output evaluators."""

    name: str = "base"

    @abstractmethod
    def evaluate(self, expected: str, output: Any) -> tuple[bool, float]:
        """Return ``(passed, score)`` given the expected marker and output."""

    def outcome(
        self,
        *,
        sample_id: str,
        agent_id: str,
        expected: str,
        output: Any,
        error: str | None = None,
        duration_ms: float = 0.0,
    ) -> EvalOutcome:
        passed, score = (False, 0.0) if error else self.evaluate(expected, output)
        if error:
            passed, score = False, 0.0
        return EvalOutcome(
            sample_id=sample_id,
            agent_id=agent_id,
            status="failed" if (error or not passed) else "completed",
            passed=passed,
            score=score,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )


def _dumps(output: Any) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    try:
        import json

        return json.dumps(output, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(output)


class KeywordEvaluator(BaseEvaluator):
    """Checks whether a required substring (or any of several) appears."""

    name = "keyword"

    def __init__(self) -> None:
        import re

        self._re = re

    def evaluate(self, expected: str, output: Any) -> tuple[bool, float]:
        text = _dumps(output).lower()
        candidates = [c.strip() for c in expected.split("||") if c.strip()]
        if not candidates:
            return False, 0.0
        hits = sum(1 for c in candidates if c.lower() in text)
        passed = hits > 0
        score = hits / len(candidates)
        return passed, score


class EvaluatorRegistry:
    """Names to evaluator instances."""

    def __init__(self) -> None:
        self._evaluators: dict[str, BaseEvaluator] = {
            "keyword": KeywordEvaluator(),
        }

    def register(self, name: str, evaluator: BaseEvaluator) -> None:
        self._evaluators[name] = evaluator

    def get(self, name: str) -> BaseEvaluator:
        try:
            return self._evaluators[name]
        except KeyError:
            raise ValueError(f"unknown evaluator {name!r}: {sorted(self._evaluators)}") from None

    def names(self) -> list[str]:
        return sorted(self._evaluators)


__all__ = ["ALLOWED_KEYWORDS", "BaseEvaluator", "EvaluatorRegistry", "KeywordEvaluator", "_dumps"]
