"""
Tests for configuration system.

Added 2025-07-05: Tests for Config class and YAML loading.
"""

from pathlib import Path

from common.config import Config


def test_config_creation():
    """Test basic Config creation."""
    config = Config()

    # Test default values are loaded
    assert config.gateway is not None
    assert config.router is not None
    assert hasattr(config.gateway, "connection_timeout")
    assert hasattr(config.router, "request_timeout")


def test_config_gateway_settings():
    """Test gateway configuration settings."""
    config = Config()

    # Gateway settings should have reasonable defaults
    assert config.gateway.connection_timeout > 0
    assert isinstance(config.gateway.connection_timeout, (int, float))


def test_config_router_settings():
    """Test router configuration settings."""
    config = Config()

    # Router settings should have reasonable defaults
    assert config.router.request_timeout > 0
    assert config.router.max_retries >= 0
    assert isinstance(config.router.request_timeout, (int, float))
    assert isinstance(config.router.max_retries, int)


def test_config_string_representation():
    """Test that config can be represented as string."""
    config = Config()
    config_str = str(config)

    # Should be able to convert to string without errors
    assert isinstance(config_str, str)
    assert len(config_str) > 0


def test_config_yaml_file_exists():
    """Test that config.yaml file exists."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml file should exist in the project root"


def test_config_attributes_exist():
    """Test that required config attributes exist."""
    config = Config()

    # Should have main sections
    assert hasattr(config, "gateway")
    assert hasattr(config, "router")

    # Gateway section should have expected attributes
    gateway = config.gateway
    expected_gateway_attrs = ["connection_timeout"]
    for attr in expected_gateway_attrs:
        assert hasattr(gateway, attr), f"Gateway should have {attr} attribute"

    # Router section should have expected attributes
    router = config.router
    expected_router_attrs = ["request_timeout", "max_retries"]
    for attr in expected_router_attrs:
        assert hasattr(router, attr), f"Router should have {attr} attribute"


def test_config_values_are_reasonable():
    """Test that config values are within reasonable ranges."""
    config = Config()

    # Timeouts should be positive and reasonable (not too high)
    assert 1 <= config.gateway.connection_timeout <= 3600  # 1 second to 1 hour
    assert 1 <= config.router.request_timeout <= 3600  # 1 second to 1 hour

    # Max retries should be reasonable
    assert 0 <= config.router.max_retries <= 10
