"""
Runtime configuration file persistence for MCP server.

This module is now a simple file helper that reads/writes configuration
for the MCP 2025 server, which is the single source of truth.

Following PROJECT_RULES.md:
- Single responsibility: File persistence only
- MCP server handles all configuration logic
- No caching or state management here
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from common.logging import get_logger

logger = get_logger(__name__)


class RuntimeConfigPersistence:
    """Simple file persistence for MCP server configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize runtime config persistence."""
        self.config_path = config_path or Path("runtime_config.yaml")

        # Ensure config file exists with defaults
        self._ensure_config_file()

    def _ensure_config_file(self) -> None:
        """Ensure runtime config file exists with defaults."""
        if not self.config_path.exists():
            logger.info(
                event="runtime_config_created",
                message="Creating default runtime config file",
                path=str(self.config_path),
            )

            default_config = {
                "provider": {
                    "active": "openai",
                    "models": {
                        "openai": {
                            "model": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": None,
                            "system_prompt": "You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
                        },
                        "anthropic": {
                            "model": "claude-3-5-sonnet-20241022",
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "system_prompt": "You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
                        },
                        "gemini": {
                            "model": "gemini-1.5-flash",
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "system_prompt": "You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
                        },
                        "openrouter": {
                            "model": "anthropic/claude-3-sonnet",
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "system_prompt": "You are a helpful AI assistant with access to smart home devices. When users ask to control devices, use the available functions to execute their requests.",
                        },
                    },
                },
                "runtime": {"strict_mode": True, "config_reload_interval": 5},
            }

            self.save_config(default_config)

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            logger.debug(
                event="config_loaded",
                message="Configuration loaded from file",
                path=str(self.config_path),
            )

            return config

        except Exception as e:
            logger.error(
                event="config_load_failed", message="Failed to load configuration", error=str(e)
            )
            # Return empty config on error
            return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary to save

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)

            logger.info(
                event="config_saved",
                message="Configuration saved to file",
                path=str(self.config_path),
            )

            return True

        except Exception as e:
            logger.error(
                event="config_save_failed", message="Failed to save configuration", error=str(e)
            )
            return False


# Global persistence instance
_persistence = None


def get_runtime_config_persistence() -> RuntimeConfigPersistence:
    """Get global runtime config persistence instance."""
    global _persistence
    if _persistence is None:
        _persistence = RuntimeConfigPersistence()
    return _persistence
