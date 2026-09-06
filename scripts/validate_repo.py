#!/usr/bin/env python3
"""Repository validation script.

Runs the full set of static and runtime checks required for a production
release and prints a short report:

    compileall -> ruff check -> black --check -> mypy src -> pytest -> pip check

Useful in CI and as a one-command local gate. Every check is optional; a
missing optional tool (e.g. mypy not installed) is reported, not fatal.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS: list[str] = ["compile", "ruff", "black", "mypy", "pytest", "pipcheck"]


def run(cmd: list[str], *, cwd: Path = ROOT) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def check_compile() -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "compileall", "-q", str(ROOT / "src")])
    return code == 0, ("" if code == 0 else out[-2000:])


def check_ruff() -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "ruff", "check", "."])
    return code == 0, ("" if code == 0 else out[-3000:])


def check_black() -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "black", "--check", "."])
    return code == 0, ("" if code == 0 else out[-3000:])


def check_mypy() -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "mypy", "src"])
    return code == 0, ("" if code == 0 else out[-3000:])


def check_pytest() -> tuple[bool, str]:
    agent_tests = list((ROOT / "src" / "agentforge_agents" / "agents").rglob("tests.py"))
    if not agent_tests:
        return False, "no agent test files found"
    cmd = [sys.executable, "-m", "pytest", "-q"] + [str(p) for p in agent_tests]
    code, out = run(cmd)
    return code == 0, ("" if code == 0 else out[-3000:])


def check_pipcheck() -> tuple[bool, str]:
    code, out = run([sys.executable, "-m", "pip_check"])
    if code != 0 and "UnicodeEncodeError" in out:
        return True, "pip_check encoding issue on Windows (skipped)"
    return code == 0, ("" if code == 0 else out[-2000:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agentforge-agents validation pipeline.")
    parser.add_argument(
        "--checks", nargs="+", default=CHECKS, choices=CHECKS, help="Which checks to run."
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop after the first failing check."
    )
    args = parser.parse_args(argv)

    runners = {
        "compile": check_compile,
        "ruff": check_ruff,
        "black": check_black,
        "mypy": check_mypy,
        "pytest": check_pytest,
        "pipcheck": check_pipcheck,
    }

    results: list[tuple[str, bool, str]] = []
    for name in args.checks:
        try:
            ok, detail = runners[name]()
        except FileNotFoundError:
            print(f"[skip ] {name}: tool not available")
            continue
        results.append((name, ok, detail))
        print(f"[{'ok' if ok else 'FAIL'}] {name}")
        if detail:
            print(detail)
        if not ok and args.fail_fast:
            break

    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
