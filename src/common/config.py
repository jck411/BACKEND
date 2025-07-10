"""
Configuration loader for the backend project.

Loads settings from config.yaml. Environment variables are used ONLY for secrets.
Following PROJECT_RULES.md security rules - never log secrets.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class GatewayConfig(BaseModel):
    """Configuration for the WebSocket gateway."""

    host: str = Field(default="127.0.0.1", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    max_connections: int = Field(default=100, description="Maximum concurrent connections")
    connection_timeout: int = Field(default=300, description="Connection timeout in seconds")
    max_upload_size: int = Field(
        default=50 * 1024 * 1024, description="Maximum upload size in bytes (50MB)"
    )


class RouterConfig(BaseModel):
    """Configuration for the router component."""

    request_timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class ProviderConfig(BaseModel):
    """Configuration for AI providers - runtime configurable."""

    # Provider selection (no fallbacks - strict mode)
    active: str = Field(
        default="openai", description="Active provider (openai|anthropic|gemini|openrouter)"
    )

    # Strict mode: fail fast if provider unavailable (no fallbacks)
    strict_mode: bool = Field(default=True, description="Strict mode - no fallbacks")

    # OpenAI settings
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.7, description="OpenAI temperature setting")
    openai_max_tokens: Optional[int] = Field(default=None, description="OpenAI max tokens limit")
    openai_system_prompt: str = Field(
        default="You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
        description="System prompt for OpenAI",
    )

    # Anthropic settings (temporary - will move to MCP)
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic model to use"
    )
    anthropic_temperature: float = Field(default=0.7, description="Anthropic temperature setting")
    anthropic_max_tokens: int = Field(default=4096, description="Anthropic max tokens limit")
    anthropic_system_prompt: str = Field(
        default="You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
        description="System prompt for Anthropic",
    )

    # Gemini settings (temporary - will move to MCP)
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model to use")
    gemini_temperature: float = Field(default=0.7, description="Gemini temperature setting")
    gemini_max_tokens: int = Field(default=4096, description="Gemini max tokens limit")
    gemini_system_prompt: str = Field(
        default="You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
        description="System prompt for Gemini",
    )

    # OpenRouter settings (temporary - will move to MCP)
    openrouter_model: str = Field(
        default="anthropic/claude-3-sonnet", description="OpenRouter model to use"
    )
    openrouter_temperature: float = Field(default=0.7, description="OpenRouter temperature setting")
    openrouter_max_tokens: int = Field(default=4096, description="OpenRouter max tokens limit")
    openrouter_system_prompt: str = Field(
        default="You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
        description="System prompt for OpenRouter",
    )


class MCPConfig(BaseModel):
    """Configuration for the MCP service."""

    database_path: str = Field(default="mcp.db", description="SQLite database path")
    redis_url: Optional[str] = Field(default=None, description="Redis URL for pub/sub")


class Config(BaseModel):
    """Main configuration object."""

    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    router: RouterConfig = Field(default_factory=RouterConfig)
    providers: ProviderConfig = Field(default_factory=ProviderConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    log_level: str = Field(default="INFO", description="Logging level")
    enable_pretty_print: bool = Field(
        default=False, description="Enable custom pretty print for debugging"
    )
    enable_jq_json_formatting: bool = Field(
        default=False, description="Enable jq-style JSON formatting for logs"
    )
    save_to_file: bool = Field(default=False, description="Save logs to file")
    log_file_path: str = Field(default="server.log", description="Log file path (relative to root)")
    max_log_file_size: int = Field(
        default=10485760, description="Max log file size in bytes (10MB)"
    )
    backup_count: int = Field(default=5, description="Number of backup log files to keep")


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file.

    Environment variables are used ONLY for secrets (API keys), not configuration.
    All configuration options must be set in config.yaml or runtime_config.yaml.

    Args:
        config_path: Path to config.yaml file. Defaults to ./config.yaml

    Returns:
        Loaded configuration object
    """
    if config_path is None:
        config_path = Path("config.yaml")

    config_data: Dict[str, Any] = {}

    # Load from YAML file if it exists
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    # Handle nested logging configuration
    if "logging" in config_data:
        logging_config = config_data["logging"]
        if "level" in logging_config:
            config_data["log_level"] = logging_config["level"]
        if "enable_pretty_print" in logging_config:
            config_data["enable_pretty_print"] = logging_config["enable_pretty_print"]
        if "enable_jq_json_formatting" in logging_config:
            config_data["enable_jq_json_formatting"] = logging_config["enable_jq_json_formatting"]
        if "save_to_file" in logging_config:
            config_data["save_to_file"] = logging_config["save_to_file"]
        if "log_file_path" in logging_config:
            config_data["log_file_path"] = logging_config["log_file_path"]
        if "max_log_file_size" in logging_config:
            config_data["max_log_file_size"] = logging_config["max_log_file_size"]
        if "backup_count" in logging_config:
            config_data["backup_count"] = logging_config["backup_count"]

    # Environment variables are ONLY for secrets/API keys, not configuration
    # All configuration should be in config.yaml or runtime_config.yaml

    return Config(**config_data)
