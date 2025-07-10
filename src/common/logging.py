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

# Global config reference for pretty print setting
_config: Optional[Config] = None


def pretty_renderer(_, __, event_dict) -> str:
    """
    Custom renderer that formats logs with line breaks after commas
    and removes timestamps, logger level, and logger names when pretty print is enabled.
    """
    global _config

    # If pretty print is not enabled, fall back to JSON
    if not _config or not _config.enable_pretty_print:
        result = structlog.processors.JSONRenderer()(_, __, event_dict)
        return str(result)

    # Regular pretty printing
    # Remove unwanted fields for pretty printing
    filtered_dict = {
        k: v for k, v in event_dict.items() if k not in ["timestamp", "level", "logger"]
    }

    # Format the event specially
    event = filtered_dict.pop("event", "unknown_event")
    output_lines = [f"EVENT: {event}"]

    # Format each key-value pair
    for key, value in filtered_dict.items():
        if isinstance(value, (dict, list)):
            # Convert to string and add line breaks after commas
            value_str = str(value)
            formatted_value = value_str.replace(", ", ",\n    ")
            output_lines.append(f"{key}: {formatted_value}")
        else:
            output_lines.append(f"{key}: {value}")

    output_lines.append("-" * 50)
    return "\n".join(output_lines)


def setup_logging(config: Config) -> None:
    """
    Setup structured JSON logging using structlog.

    Args:
        config: Application configuration
    """
    global _config
    _config = config

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            pretty_renderer,  # Use our custom renderer instead of JSONRenderer
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


def pretty_log(event: str, **kwargs: Any) -> None:
    """
    Simple pretty printer for debugging - bypasses structured logging entirely.
    Only prints if enable_pretty_print is True in config.

    Format:
    - No timestamps, logger level, or logger names
    - Line break after every comma in key-value pairs
    - Clean, readable output for debugging

    Args:
        event: Event name
        **kwargs: Key-value pairs to print
    """
    global _config

    # Only print if pretty print is enabled in config
    if not _config or not _config.enable_pretty_print:
        return

    print(f"EVENT: {event}")
    for key, value in kwargs.items():
        # Convert value to string and format with line breaks after commas
        if isinstance(value, (dict, list)):
            value_str = str(value)
            # Add line breaks after commas
            formatted_value = value_str.replace(", ", ",\n    ")
            print(f"{key}: {formatted_value}")
        else:
            print(f"{key}: {value}")
    print("-" * 50)
