PYTHON ?= python
PIP ?= pip

.PHONY: help install dev-install lint format typecheck test coverage compile smoke benchmark \
	validate docker-build docker-up docker-down docs clean

help:
	@echo "agentforge-agents targets:"
	@echo "  install        Install production dependencies"
	@echo "  dev-install    Install development + production dependencies"
	@echo "  lint           Run ruff check"
	@echo "  format-check   Run black --check"
	@echo "  format         Run black"
	@echo "  typecheck      Run mypy"
	@echo "  test           Run pytest"
	@echo "  coverage       Run pytest with coverage (requires 90%+)"
	@echo "  compile        Run compileall on src"
	@echo "  smoke          Run smoke tests"
	@echo "  benchmark      Run evaluation benchmark CLI"
	@echo "  validate       Run the full validation pipeline"
	@echo "  docker-build   Build production image"
	@echo "  docker-up      Start docker-compose stack"
	@echo "  docker-down    Stop docker-compose stack"
	@echo "  docs           Preview documentation (markdown server)"
	@echo "  clean          Remove caches and build artifacts"

install:
	$(PIP) install -e .

dev-install:
	$(PIP) install -e ".[dev,llm]"

lint:
	ruff check .

format-check:
	black --check .

format:
	black .

typecheck:
	mypy src

test:
	pytest -v

coverage:
	pytest --cov=agentforge_agents --cov-report=term-missing --cov-fail-under=90

compile:
	$(PYTHON) -m compileall -q src

smoke:
	pytest -m smoke -v

benchmark:
	$(PYTHON) scripts/benchmark.py

validate: lint format-check typecheck compile test pipcheck

pipcheck:
	$(PIP) check

docker-build:
	docker build -t agentforge-agents:prod -f docker/Dockerfile.prod .

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docs:
	markdown README.md docs/ > /dev/null 2>&1 || echo "Install 'markdown' extra for docs preview"

clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info