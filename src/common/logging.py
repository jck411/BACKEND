"""
Structured JSON logging setup for the backend project using structlog.

Following PROJECT_RULES.md:
- Use structlog for structured JSON logging
- Include event, module, and elapsed_ms fields
- Never log tokens, secrets, or PII
"""

import json
import logging
import logging.handlers
import subprocess
import time
from typing import Any, Optional

import structlog

from common.config import Config

# Global config reference for pretty print setting
_config: Optional[Config] = None


def jq_format_json(json_str: str) -> str:
    """
    Format JSON string using jq-style pretty printing.
    Falls back to regular JSON pretty printing if jq is not available.
    """
    try:
        # Try to use jq for formatting if available
        result = subprocess.run(
            ["jq", "."], input=json_str, text=True, capture_output=True, timeout=1
        )
        if result.returncode == 0:
            return result.stdout.rstrip()
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Fallback to Python's json formatting
    try:
        parsed = json.loads(json_str)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        return json_str


def pretty_renderer(_, __, event_dict) -> str:
    """
    Custom renderer that formats logs based on configuration:
    - enable_jq_json_formatting: Uses jq-style JSON formatting
    - enable_pretty_print: Uses custom pretty format (removes timestamps, etc.)
    - Neither: Uses compact JSON format
    """
    global _config

    # Generate JSON first
    json_result = structlog.processors.JSONRenderer()(_, __, event_dict)
    json_str = str(json_result)

    # If jq formatting is enabled, use that
    if _config and _config.enable_jq_json_formatting:
        return jq_format_json(json_str)

    # If pretty print is enabled, use custom formatting
    if _config and _config.enable_pretty_print:
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

    # Default: return compact JSON
    return json_str


def setup_logging(config: Config) -> None:
    """
    Setup structured JSON logging using structlog.

    Args:
        config: Application configuration
    """
    global _config
    _config = config

    # If tool_calls_only mode is enabled, set very high log level to suppress normal logs
    if config.log_tool_calls_only:
        log_level = logging.CRITICAL + 1  # Higher than CRITICAL to suppress everything
    else:
        log_level = getattr(logging, config.log_level.upper())

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

    # Set up handlers
    handlers = []

    # Console handler (always present)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    handlers.append(console_handler)

    # File handler (if enabled)
    if config.save_to_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file_path,
            maxBytes=config.max_log_file_size,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(file_handler)

    # Set log level and handlers
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format="%(message)s",
    )

    # Set specific logger levels - suppress if tool_calls_only mode
    if config.log_tool_calls_only:
        logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL + 1)
        logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL + 1)
        logging.getLogger().setLevel(logging.CRITICAL + 1)
    else:
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


def log_startup_message(message: str, **kwargs: Any) -> None:
    """
    Log critical startup messages even when log_tool_calls_only is enabled.
    These are essential for knowing the application is running.
    """
    global _config

    if _config and _config.log_tool_calls_only:
        # In tool calls only mode, show startup info with clear prefix
        print(f"🚀 STARTUP: {message}")
        if kwargs:
            for key, value in kwargs.items():
                print(f"   {key}: {value}")
        print("-" * 50)
    else:
        # Normal mode - use regular structured logging
        logger = get_logger("startup")
        logger.info(message, **kwargs)


def should_suppress_normal_logs() -> bool:
    """Check if normal logs should be suppressed (tool calls only mode)."""
    global _config
    return bool(_config and _config.log_tool_calls_only)


def log_tool_call_json(event: str, json_data: Any, direction: str = "unknown") -> None:
    """
    Log tool call JSON data when log_tool_calls_only is enabled.
    This bypasses all normal logging and only prints tool call JSON.

    Args:
        event: Event name (e.g., "tool_request", "tool_response")
        json_data: The JSON data to log
        direction: Direction of communication ("outgoing", "incoming")
    """
    global _config

    # Only log if tool calls only mode is enabled
    if not _config or not _config.log_tool_calls_only:
        return

    # Create a simple, clean JSON log entry
    log_entry = {
        "tool_call_event": event,
        "direction": direction,
        "timestamp": time.time(),
        "data": json_data,
    }

    # Print directly to console and file (bypass all other logging)
    json_output = json.dumps(log_entry, indent=2)
    print(json_output)

    # Also write to file if file logging is enabled
    if _config.save_to_file:
        try:
            with open(_config.log_file_path, "a", encoding="utf-8") as f:
                f.write(json_output + "\n")
        except Exception:
            pass  # Fail silently for file logging


def should_log_adapter_details() -> bool:
    """Check if adapter details should be logged (opposite of tool calls only mode)."""
    global _config
    return not (_config and _config.log_tool_calls_only)


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
