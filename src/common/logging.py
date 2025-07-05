"""
Structured JSON logging setup for the backend project.

Following PROJECT_RULES.md:
- Emit structured JSON logs with event, module, and elapsed_ms
- Never log tokens, secrets, or PII
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from common.config import Config


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }

        # Add elapsed_ms if available
        if hasattr(record, "elapsed_ms"):
            log_data["elapsed_ms"] = getattr(record, "elapsed_ms")

        # Add extra fields from the log record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "event",
                "elapsed_ms",
            ):
                log_data[key] = value

        return json.dumps(log_data, default=str, ensure_ascii=False)


def setup_logging(config: Config) -> None:
    """
    Setup structured JSON logging for the application.

    Args:
        config: Application configuration
    """
    # Remove all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with structured formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())

    # Configure root logger
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, config.log_level.upper()))

    # Set specific logger levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


class TimedLogger:
    """Context manager for timing operations and logging elapsed time."""

    def __init__(self, logger: logging.Logger, event: str, **kwargs: Any):
        self.logger = logger
        self.event = event
        self.extra = kwargs
        self.start_time: Optional[float] = None

    def __enter__(self) -> "TimedLogger":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            self.logger.info(
                self.event,
                extra={"event": self.event, "elapsed_ms": round(elapsed_ms, 2), **self.extra},
            )
