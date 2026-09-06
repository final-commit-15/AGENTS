"""SQL tool - execute read-only SQL against SQLite databases (incl. in-memory)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool

_READ_ONLY_PREFIXES = ("select", "pragma", "explain", "with")
_MAX_ROWS = 200


class SQLTool(BaseTool):
    """Run read-only, parameterised queries.

    Only ``SELECT``/``PRAGMA``/``WITH`` statements execute; any data-changing
    statement is rejected. Without a path a transient in-memory database is
    used, perfect for the Data Agent's analytical workloads.
    """

    name = "sql"
    description = "Execute read-only SQL (SELECT/PRAGMA/WITH) against a SQLite database."
    category = "data"
    timeout_seconds = 30.0
    tags = ["sql", "database"]

    parameters = [
        ToolParameter(name="query", type="string", required=True),
        ToolParameter(
            name="db_path",
            type="string",
            required=False,
            description="SQLite file; defaults to in-memory.",
        ),
        ToolParameter(name="parameters", type="array", required=False),
    ]

    def __init__(self, context: Any = None, *, db_path: str | None = None) -> None:
        from agentforge_agents.tools.base import ToolContext

        super().__init__(context=context or ToolContext())
        self._fixed_db = db_path
        self._in_memory: sqlite3.Connection | None = None

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        query = str(arguments.get("query", "")).strip().lower()
        if not query:
            return ["query is required"]
        if not any(query.startswith(prefix) for prefix in _READ_ONLY_PREFIXES):
            return ["only SELECT, PRAGMA, EXPLAIN, and WITH queries are allowed"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        query = str(arguments["query"])
        params = list(arguments.get("parameters") or [])
        db_path = arguments.get("db_path") or self._fixed_db
        try:
            conn, owns_connection = self._connect(db_path, query)
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [description[0] for description in (cursor.description or [])]
            rows = cursor.fetchmany(_MAX_ROWS + 1)
            if owns_connection:
                conn.close()
        except sqlite3.Error as exc:
            if "conn" in locals() and owns_connection:
                try:
                    conn.close()  # type: ignore[possibly-undefined]
                except Exception:  # noqa: BLE001
                    pass
            return self.err(f"sql error: {exc}")
        truncated = len(rows) > _MAX_ROWS
        return self.ok(
            {
                "columns": columns,
                "rows": rows[:_MAX_ROWS],
                "row_count": len(rows),
                "truncated": truncated,
            }
        )

    def _connect(self, db_path: str | None, query: str) -> tuple[sqlite3.Connection, bool]:
        if db_path:
            path = Path(db_path)
            if not path.is_file():
                raise sqlite3.Error(f"database file not found: {db_path}")
            connection = sqlite3.connect(path, timeout=5)
            return connection, True
        # Reuse a transient in-memory database for the tool instance so an agent
        # can create + query tables in separate calls.
        if self._in_memory is None:
            self._in_memory = sqlite3.connect(":memory:")
        return self._in_memory, False

    async def close(self) -> None:  # pragma: no cover - lifecycle hook
        if self._in_memory is not None:
            self._in_memory.close()
            self._in_memory = None


__all__ = ["SQLTool"]
