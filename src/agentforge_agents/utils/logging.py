"""Structured logging utilities built on structlog.

Call :func:`configure_logging` once at application startup to wire processors.
:func:`get_logger` returns a structlog bound logger that also exposes a
``warning`` alias (compatible with stdlib loggers).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


class AgentForgeLogger(structlog.BoundLoggerBase):
    """structlog bound logger with a stdlib-compatible ``warning`` alias."""

    def warning(self, event: str | None = None, **kw: Any) -> Any:
        return self.warn(event, **kw)

    def debug(self, event: str | None = None, **kw: Any) -> Any:
        return self._proxy_to_logger("debug", event, **kw)

    def info(self, event: str | None = None, **kw: Any) -> Any:
        return self._proxy_to_logger("info", event, **kw)

    def warn(self, event: str | None = None, **kw: Any) -> Any:
        return self._proxy_to_logger("warn", event, **kw)

    def error(self, event: str | None = None, **kw: Any) -> Any:
        return self._proxy_to_logger("error", event, **kw)

    def critical(self, event: str | None = None, **kw: Any) -> Any:
        return self._proxy_to_logger("critical", event, **kw)

    def exception(self, event: str | None = None, **kw: Any) -> Any:
        kw.setdefault("exc_info", True)
        return self._proxy_to_logger("exception", event, **kw)


_METHODS = ("debug", "info", "warn", "warning", "error", "critical", "exception")
structlog.configure(wrapper_class=AgentForgeLogger, cache_logger_on_first_use=True)


def configure_logging(level: str | None = None, *, json: bool = False) -> None:
    """Configure structlog and the stdlib root logger.

    ``json=True`` renders one JSON object per line for production ingestion.
    """
    level_name = (level or "INFO").upper()
    numeric = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=numeric, stream=sys.stdout, force=True)

    renderer: Any = (
        structlog.processors.JSONRenderer(ensure_ascii=False)
        if json
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=AgentForgeLogger,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "agentforge") -> AgentForgeLogger:
    """Return a bound structlog logger with a ``warning`` alias."""
    return structlog.get_logger(name)  # type: ignore[return-value]


__all__ = ["AgentForgeLogger", "configure_logging", "get_logger"]
