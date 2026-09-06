"""AgentForge Agents - modular AI agent framework.

This package provides:

* A strongly typed agent framework (``core``).
* Ten production-ready specialized agents (``agents``).
* Multi-agent orchestration (``orchestration``).
* A centralized tool registry with permission checks (``tools``).
* Short- and long-term memory with vector retrieval (``memory``).
* An asynchronous execution engine with sandboxing (``execution``).
* An event-driven bus with local / Redis / WebSocket adapters (``events``).
* Pydantic schemas shared with the rest of AgentForge (``schemas``).
* YAML configuration with environment overrides (``config``).
* An evaluation framework (``evals``).
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__"]
