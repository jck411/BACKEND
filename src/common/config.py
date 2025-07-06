"""
Configuration loader for the backend project.

Loads settings from config.yaml and environment variables.
Following PROJECT_RULES.md security rules - never log secrets.
"""

import os
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
    """Temporary configuration for AI providers (will move to MCP later)."""

    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.7, description="OpenAI temperature setting")
    openai_max_tokens: Optional[int] = Field(default=None, description="OpenAI max tokens limit")
    openai_system_prompt: str = Field(
        default="You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
        description="System prompt for OpenAI",
    )

    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic model to use"
    )
    anthropic_temperature: float = Field(default=0.7, description="Anthropic temperature setting")
    anthropic_max_tokens: int = Field(default=4096, description="Anthropic max tokens limit")


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


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

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

    # Override with environment variables
    # Gateway config
    if "GATEWAY_HOST" in os.environ:
        config_data.setdefault("gateway", {})["host"] = os.environ["GATEWAY_HOST"]
    if "GATEWAY_PORT" in os.environ:
        config_data.setdefault("gateway", {})["port"] = int(os.environ["GATEWAY_PORT"])

    # Router config
    if "ROUTER_TIMEOUT" in os.environ:
        config_data.setdefault("router", {})["request_timeout"] = int(os.environ["ROUTER_TIMEOUT"])

    # MCP config
    if "MCP_DATABASE_PATH" in os.environ:
        config_data.setdefault("mcp", {})["database_path"] = os.environ["MCP_DATABASE_PATH"]
    if "REDIS_URL" in os.environ:
        config_data.setdefault("mcp", {})["redis_url"] = os.environ["REDIS_URL"]

    # Logging
    if "LOG_LEVEL" in os.environ:
        config_data["log_level"] = os.environ["LOG_LEVEL"]

    return Config(**config_data)
