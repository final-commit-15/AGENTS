"""Dataset loading for evaluations."""

from __future__ import annotations

import json
from pathlib import Path

from agentforge_agents.evals.schemas import EvalSample
from agentforge_agents.utils.logging import get_logger

log = get_logger(__name__)

BUILTIN_DATASET_PACKAGE = "agentforge_agents.evals.datasets"
DATASETS_DIR = Path(__file__).parent / "datasets"

EVAL_DATASETS = [
    "planner",
    "coding",
    "research",
    "data",
    "automation",
    "browser",
    "document",
    "memory",
    "workflow",
    "communication",
]


class DatasetLoader:
    """Loads evaluation samples from JSON/JSONL files or built-in datasets."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or DATASETS_DIR

    def load(self, name: str) -> list[EvalSample]:
        candidates = [
            self.directory / f"{name}.json",
            self.directory / f"{name}.jsonl",
        ]
        for path in candidates:
            if path.exists():
                return self._load_file(path)
        raise FileNotFoundError(f"no eval dataset named {name!r} under {self.directory}")

    def _load_file(self, path: Path) -> list[EvalSample]:
        samples: list[EvalSample] = []
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".jsonl":
            for line in text.splitlines():
                line = line.strip()
                if line:
                    samples.append(EvalSample.model_validate(json.loads(line)))
        else:
            data = json.loads(text)
            items = data.get("samples", data) if isinstance(data, dict) else data
            for item in items:
                samples.append(EvalSample.model_validate(item))
        log.info("loaded_dataset", name=path.stem, samples=len(samples))
        return samples

    def available(self) -> list[str]:
        names: list[str] = []
        for path in sorted(self.directory.iterdir()):
            if path.suffix in {".json", ".jsonl"} and path.stem not in names:
                names.append(path.stem)
        return names


def load_dataset(name: str, *, directory: str | None = None) -> list[EvalSample]:
    loader = DatasetLoader(Path(directory) if directory else None)
    return loader.load(name)


__all__ = ["DATASETS_DIR", "EVAL_DATASETS", "DatasetLoader", "load_dataset"]
