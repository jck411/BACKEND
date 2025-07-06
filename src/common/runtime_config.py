"""
Runtime configuration management for AI providers.

This module handles runtime-configurable settings that can be changed
without restarting the application. In the future, this will integrate
with frontend commands for dynamic provider switching.

Following PROJECT_RULES.md:
- Single responsibility: Runtime configuration management
- Future-ready for MCP integration
- Environment variables only for secrets (API keys)
- Configuration files for runtime settings
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field

from common.logging import get_logger

logger = get_logger(__name__)


class ModelConfig(BaseModel):
    """Configuration for a specific AI model."""

    model: str = Field(description="Model identifier")
    temperature: float = Field(default=0.7, description="Temperature setting")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens limit")
    system_prompt: str = Field(description="System prompt for the model")


class RuntimeProviderConfig(BaseModel):
    """Runtime configuration for AI provider selection."""

    active: str = Field(description="Active provider")
    models: Dict[str, ModelConfig] = Field(description="Model configurations")


class RuntimeConfig(BaseModel):
    """Runtime behavior settings."""

    strict_mode: bool = Field(default=True, description="Strict mode - no fallbacks")
    config_reload_interval: int = Field(default=5, description="Config reload interval in seconds")


class RuntimeConfigManager:
    """Manages runtime configuration with automatic reloading."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize runtime config manager."""
        self.config_path = config_path or Path("runtime_config.yaml")
        self.last_modified = 0.0
        self._cached_config = None

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

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)

    def _should_reload(self) -> bool:
        """Check if config file has been modified."""
        if not self.config_path.exists():
            return False

        current_modified = self.config_path.stat().st_mtime
        if current_modified > self.last_modified:
            self.last_modified = current_modified
            return True
        return False

    def load_runtime_config(self) -> Dict[str, Any]:
        """Load runtime configuration with automatic reloading."""
        if self._cached_config is None or self._should_reload():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._cached_config = yaml.safe_load(f) or {}

            logger.info(
                event="runtime_config_loaded",
                message="Runtime configuration loaded",
                active_provider=self._cached_config.get("provider", {}).get("active"),
                strict_mode=self._cached_config.get("runtime", {}).get("strict_mode", True),
            )

        return self._cached_config

    def get_active_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the currently active provider."""
        config = self.load_runtime_config()
        provider_config = config.get("provider", {})
        active_provider = provider_config.get("active", "openai")

        # Get model config for active provider
        models = provider_config.get("models", {})
        active_model_config = models.get(active_provider, {})

        return {
            "provider": active_provider,
            "model": active_model_config.get("model", "gpt-4o-mini"),
            "temperature": active_model_config.get("temperature", 0.7),
            "max_tokens": active_model_config.get("max_tokens"),
            "system_prompt": active_model_config.get(
                "system_prompt", "You are a helpful AI assistant."
            ),
        }

    def is_strict_mode(self) -> bool:
        """Check if strict mode is enabled (no fallbacks)."""
        config = self.load_runtime_config()
        return config.get("runtime", {}).get("strict_mode", True)

    def update_active_provider(self, provider: str) -> bool:
        """
        Update active provider in runtime config.

        Args:
            provider: Provider name (openai|anthropic|gemini|openrouter)

        Returns:
            True if update successful, False otherwise
        """
        try:
            config = self.load_runtime_config()

            # Validate provider exists in models
            available_providers = config.get("provider", {}).get("models", {}).keys()
            if provider not in available_providers:
                logger.error(
                    event="invalid_provider",
                    message="Invalid provider specified",
                    provider=provider,
                    available=list(available_providers),
                )
                return False

            # Update config
            config.setdefault("provider", {})["active"] = provider

            # Write back to file
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)

            # Invalidate cache
            self._cached_config = None

            logger.info(
                event="provider_updated", message="Active provider updated", new_provider=provider
            )

            return True

        except Exception as e:
            logger.error(
                event="provider_update_failed",
                message="Failed to update active provider",
                provider=provider,
                error=str(e),
            )
            return False


# Global runtime config manager instance
_runtime_config_manager = None


def get_runtime_config_manager() -> RuntimeConfigManager:
    """Get global runtime config manager instance."""
    global _runtime_config_manager
    if _runtime_config_manager is None:
        _runtime_config_manager = RuntimeConfigManager()
    return _runtime_config_manager


def get_active_provider_config() -> Dict[str, Any]:
    """Get configuration for the currently active provider."""
    return get_runtime_config_manager().get_active_provider_config()


def update_active_provider(provider: str) -> bool:
    """Update the active provider at runtime."""
    return get_runtime_config_manager().update_active_provider(provider)


def is_strict_mode() -> bool:
    """Check if strict mode is enabled."""
    return get_runtime_config_manager().is_strict_mode()
