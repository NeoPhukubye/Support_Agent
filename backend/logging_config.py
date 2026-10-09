import json
import logging
import sys
from typing import Any

from config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("supportai")
    logger.setLevel(getattr(logging, settings.log_level))

    # Clear existing handlers
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    # Use JSON format in production, human-readable in development
    if settings.log_level == "DEBUG":
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


logger = setup_logging()


def log_tool_call(tool_name: str, **kwargs: Any) -> None:
    """Log a tool call with structured data."""
    logger.info(
        "Tool call",
        extra={"extra_fields": {"tool": tool_name, "params": kwargs}},
    )


def log_agent_action(action: str, **kwargs: Any) -> None:
    """Log an agent action with structured data."""
    logger.info(
        "Agent action",
        extra={"extra_fields": {"action": action, "details": kwargs}},
    )