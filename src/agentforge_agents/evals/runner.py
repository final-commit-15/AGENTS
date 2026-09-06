"""Runner that executes eval datasets against agents and aggregates reports."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from agentforge_agents.evals.datasets import DatasetLoader
from agentforge_agents.evals.evaluators import EvaluatorRegistry
from agentforge_agents.evals.schemas import EvalConfig, EvalOutcome, EvalReport, EvalSample
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)

# Re-export the outcome/summary type aliases used in docstrings and callers.
EvalResult = EvalOutcome
EvalSummary = EvalReport


class EvaluationRunner:
    """Runs datasets against built-in agents and returns per-run reports."""

    def __init__(
        self,
        *,
        dataset_dir: str | None = None,
        evaluators: EvaluatorRegistry | None = None,
    ) -> None:
        self.dataset_loader = DatasetLoader()
        if dataset_dir:
            from pathlib import Path

            self.dataset_loader = DatasetLoader(Path(dataset_dir))
        self.evaluators = evaluators or EvaluatorRegistry()

    async def run(self, config: EvalConfig) -> list[EvalReport]:
        agents = config.agents or ["planner", "coding", "data"]
        reports: list[EvalReport] = []
        semaphore = asyncio.Semaphore(max(1, config.concurrency))
        for dataset_name in config.datasets or await self._default_datasets():
            samples = self.dataset_loader.load(dataset_name)[: config.max_samples]
            for agent_id in agents:
                report = await self._run_agent(dataset_name, agent_id, samples, semaphore, config)
                reports.append(report)
        return reports

    async def _default_datasets(self) -> list[str]:
        available = dict.fromkeys(self.dataset_loader.available(), True)
        return list(available)

    async def _run_agent(
        self,
        dataset_name: str,
        agent_id: str,
        samples: list[EvalSample],
        semaphore: asyncio.Semaphore,
        config: EvalConfig,
    ) -> EvalReport:
        agent_type = await self._build_agent_type(agent_id)
        outcomes: list[EvalOutcome] = []
        total_ms = 0.0
        for sample in samples:
            # Fresh agent per sample: run() is a one-shot lifecycle.
            instance = agent_type(_mock_config(agent_id))
            async with semaphore:
                outcome, duration = await self._run_sample(instance, sample, config)
                outcomes.append(outcome)
                total_ms += duration
        passed = sum(1 for outcome in outcomes if outcome.passed)
        total = len(outcomes)
        avg_ms = total_ms / total if total else 0.0
        report = EvalReport(
            dataset=dataset_name,
            agent_id=agent_id,
            total=total,
            passed=passed,
            failed=total - passed,
            accuracy=passed / total if total else 0.0,
            avg_duration_ms=avg_ms,
            outcomes=outcomes,
        )
        if config.report_path:
            await self._write_report(config, report)
        log.info("eval_report", dataset=dataset_name, agent=agent_id, passed=passed, total=total)
        return report

    async def _run_sample(
        self, agent: Any, sample: EvalSample, config: EvalConfig
    ) -> tuple[EvalOutcome, float]:
        from agentforge_agents.schemas.task import TaskRequest

        start = time.monotonic()
        request = TaskRequest(
            task_id=sample.id,
            instructions=sample.task,
            input={**sample.input, **(sample.input or {})},
            metadata={"eval_dataset": True},
        )
        try:
            result = await asyncio.wait_for(agent.run(request), timeout=config.timeout_seconds)
        except TimeoutError:
            duration = (time.monotonic() - start) * 1000.0
            evaluator = self.evaluators.get("keyword")
            return (
                evaluator.outcome(
                    sample_id=sample.id,
                    agent_id=agent.agent_id,
                    expected=sample.expected,
                    output=None,
                    error="timeout",
                    duration_ms=duration,
                ),
                duration,
            )
        except Exception as exc:  # noqa: BLE001
            duration = (time.monotonic() - start) * 1000.0
            evaluator = self.evaluators.get("keyword")
            return (
                evaluator.outcome(
                    sample_id=sample.id,
                    agent_id=agent.agent_id,
                    expected=sample.expected,
                    output=None,
                    error=str(exc),
                    duration_ms=duration,
                ),
                duration,
            )

        duration = (time.monotonic() - start) * 1000.0
        evaluator = self.evaluators.get("keyword")
        return (
            evaluator.outcome(
                sample_id=sample.id,
                agent_id=agent.agent_id,
                expected=sample.expected,
                output=result.output,
                error=None if result.ok() else result.error,
                duration_ms=duration,
            ),
            duration,
        )

    async def _build_agent_type(self, agent_id: str) -> Any:
        from agentforge_agents.agents import AGENT_CLASSES

        if agent_id not in AGENT_CLASSES:
            raise ValueError(f"unknown agent {agent_id!r}")
        return AGENT_CLASSES[agent_id]

    async def _write_report(self, config: EvalConfig, report: EvalReport) -> None:
        path = config.report_path or "eval-report.json"
        payload = report.model_dump(mode="json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        log.info("report_written", path=path)


def _mock_config(agent_id: str) -> Any:
    from agentforge_agents.schemas.agent import AgentConfig, MemoryConfig, ModelConfig

    return AgentConfig(
        id=agent_id,
        name=f"{agent_id} Agent",
        agent_class=f"agentforge_agents.agents.{agent_id}.agent.Agent",
        model=ModelConfig(provider="mock"),
        memory=MemoryConfig(namespace=agent_id),
    )


__all__ = ["EvalResult", "EvalSummary", "EvaluationRunner"]
