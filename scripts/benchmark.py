#!/usr/bin/env python3
"""Command-line entrypoint for the AgentForge evaluation benchmark.

Runs the built-in eval datasets against the packaged agents and writes a
machine-readable JSON report. This mirrors ``agentforge-benchmark`` for users
who prefer invoking a repo-local script.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

try:
    from agentforge_agents.evals.runner import EvaluationRunner
    from agentforge_agents.evals.schemas import EvalConfig
except ImportError:  # pragma: no cover
    print("error: agentforge_agents is not installed; run `pip install -e .`", file=sys.stderr)
    raise SystemExit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="benchmark", description="Run the AgentForge evaluation benchmark."
    )
    parser.add_argument("datasets", nargs="*", help="Dataset names (default: all).")
    parser.add_argument("--agents", nargs="*", default=None)
    parser.add_argument("--output", default="benchmark-report.json")
    parser.add_argument("--max-samples", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from agentforge_agents.evals.datasets import DatasetLoader

    loader = DatasetLoader()
    available = loader.available()
    datasets = args.datasets or available
    config = EvalConfig(
        datasets=datasets,
        agents=args.agents or ["planner", "coding", "data"],
        max_samples=args.max_samples,
        concurrency=args.concurrency,
        report_path=args.output,
    )
    runner = EvaluationRunner()
    try:
        import asyncio

        reports = asyncio.run(runner.run(config))
    except Exception as exc:  # noqa: BLE001
        print(f"error: benchmark failed: {exc}", file=sys.stderr)
        return 1

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "datasets": datasets,
        "agents": config.agents,
        "runs": [r.model_dump(mode="json") for r in reports],
        "totals": {
            "runs": len(reports),
            "total": sum(r.total for r in reports),
            "passed": sum(r.passed for r in reports),
        },
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    print(f"benchmark complete: {summary['totals']['passed']}/{summary['totals']['total']} passed")
    print(f"report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
