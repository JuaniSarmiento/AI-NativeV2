from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_obj["stack"] = self.formatStack(record.stack_info)
        # Forward any extra fields attached via LoggerAdapter or extra={}
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "taskName", "thread", "threadName",
            }:
                log_obj[key] = value
        return json.dumps(log_obj, default=str)


class _DevFormatter(logging.Formatter):
    """Human-readable format for local development."""

    _LEVEL_COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",       # cyan
        "INFO": "\033[32m",        # green
        "WARNING": "\033[33m",     # yellow
        "ERROR": "\033[31m",       # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._LEVEL_COLORS.get(record.levelname, "")
        ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
        prefix = f"{color}{record.levelname:<8}{self._RESET}"
        return f"[{ts}] {prefix} {record.name}: {record.getMessage()}"


def _build_handler(use_json: bool) -> logging.StreamHandler[Any]:
    handler: logging.StreamHandler[Any] = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter() if use_json else _DevFormatter())
    return handler


# ---------------------------------------------------------------------------
# Module-level singleton handler — avoids duplicate handlers on repeated calls
# ---------------------------------------------------------------------------
_root_configured = False


def _configure_root(level: str, use_json: bool) -> None:
    global _root_configured  # noqa: PLW0603
    if _root_configured:
        return
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    # Remove any handlers added by basicConfig or uvicorn default setup
    root.handlers.clear()
    root.addHandler(_build_handler(use_json))
    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Configuration (level, format) is lazily read from app settings on
    first call to avoid a circular import at module load time.
    """
    from app.config import get_settings  # local import to break circular dep

    settings = get_settings()
    use_json = settings.log_format.lower() == "json" and not settings.debug
    _configure_root(level=settings.log_level, use_json=use_json)
    return logging.getLogger(name)
