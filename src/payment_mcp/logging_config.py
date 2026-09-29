"""Structured logging configuration for custom-payment-mcp."""

import json
import logging
import sys
from datetime import UTC, datetime

IGNORE_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter producing structured log entries."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a structured JSON object."""
        log_payload: dict[str, str | int | float | bool | None] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra fields if provided
        for key, value in record.__dict__.items():
            if key not in IGNORE_RECORD_ATTRS and (
                isinstance(value, (str, int, float, bool)) or value is None
            ):
                log_payload[key] = value

        return json.dumps(log_payload)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for standard output.

    For stdio-based MCP servers, log messages MUST go to stderr to avoid
    corrupting the JSON-RPC communication on stdout.
    """
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
