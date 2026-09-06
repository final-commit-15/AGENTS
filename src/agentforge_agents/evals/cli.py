"""CLI entrypoint ``agentforge-benchmark``."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from agentforge_agents.evals.datasets import DatasetLoader
from agentforge_agents.evals.evaluators import EvaluatorRegistry
from agentforge_agents.evals.runner import EvaluationRunner
from agentforge_agents.evals.schemas import EvalConfig


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agentforge-benchmark",
        description="Run agent evaluation datasets and generate a report.",
    )
    parser.add_argument("datasets", nargs="*", help="Dataset names to evaluate (omit for all).")
    parser.add_argument("--agents", nargs="*", default=None, help="Agent IDs to evaluate.")
    parser.add_argument("--max-samples", type=int, default=100, help="Max samples per dataset.")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent sample executions.")
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="Per-sample timeout in seconds."
    )
    parser.add_argument("--dataset-dir", default=None, help="Directory containing eval datasets.")
    parser.add_argument("--output", default=None, help="Path for the JSON evaluation report.")
    parser.add_argument(
        "--output-format", default="json", choices=["json", "jsonl"], help="Report format."
    )
    parser.add_argument(
        "--list-datasets", action="store_true", help="List available datasets and exit."
    )
    parser.add_argument("--list-agents", action="store_true", help="List known agent IDs and exit.")
    parser.add_argument(
        "--validate", action="store_true", help="Validate datasets and inputs without running."
    )
    return parser.parse_args(argv)


async def main_async(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evaluator_registry = EvaluatorRegistry()

    if args.list_datasets:
        loader = DatasetLoader()
        for name in loader.available():
            print(name)
        return 0

    if args.list_agents:
        from agentforge_agents.agents import AGENT_CLASSES

        for name in sorted(AGENT_CLASSES):
            print(name)
        return 0

    loader = DatasetLoader(Path(args.dataset_dir) if args.dataset_dir else None)
    available = loader.available()
    datasets = args.datasets if args.datasets else available
    missing = [name for name in datasets if name not in available]
    if missing:
        print(
            f"error: unknown dataset(s): {', '.join(missing)}; available: {', '.join(available)}",
            file=sys.stderr,
        )
        return 2
    agents = args.agents or ["planner", "coding", "data"]
    config = EvalConfig(
        datasets=datasets,
        agents=agents,
        max_samples=args.max_samples,
        concurrency=max(1, args.concurrency),
        timeout_seconds=max(0.1, args.timeout),
        report_path=args.output,
        output_format=args.output_format,
    )

    runner = EvaluationRunner(
        dataset_dir=args.dataset_dir,
        evaluators=evaluator_registry,
    )
    if args.validate:
        reports = await runner.run(config)
        for report in reports:
            print(
                f"dataset={report.dataset} agent={report.agent_id} ok={report.passed}/{report.total}"
            )
        return 0
    reports = await runner.run(config)
    total = sum(r.total for r in reports)
    passed = sum(r.passed for r in reports)
    print(f"runner complete: {passed}/{total} passed across {len(reports)} run(s)")
    if not args.output and reports:
        print("Tip: use --output report.json to save a report.")
    return 0


def main(argv: list[str] | None = None) -> None:
    exit_code = asyncio.run(main_async(argv))
    raise SystemExit(exit_code)


__all__ = ["main", "main_async", "parse_args"]
