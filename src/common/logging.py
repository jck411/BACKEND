"""
Structured JSON logging setup for the backend project using structlog.

Following PROJECT_RULES.md:
- Use structlog for structured JSON logging
- Include event, module, and elapsed_ms fields
- Never log tokens, secrets, or PII
"""

import logging
import time
from typing import Any, Optional

import structlog

from common.config import Config


def setup_logging(config: Config) -> None:
    """
    Setup structured JSON logging using structlog.

    Args:
        config: Application configuration
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set log level
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(message)s",
    )

    # Set specific logger levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


class TimedLogger:
    """Context manager for timing operations and logging elapsed time using structlog."""

    def __init__(self, logger: structlog.BoundLogger, event: str, **context: Any):
        """
        Initialize timed logger.

        Args:
            logger: structlog logger instance
            event: Event name for the log entry
            **context: Additional context to include in logs
        """
        self.logger = logger
        self.event = event
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self) -> "TimedLogger":
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Log elapsed time."""
        if self.start_time is not None:
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            self.logger.info(
                self.event,
                elapsed_ms=round(elapsed_ms, 2),
                module=self.logger._context.get("logger", "unknown"),
                **self.context,
            )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)
