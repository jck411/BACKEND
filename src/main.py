"""
Main application entry point for the backend gateway.

Added 2025-07-05: Initial FastAPI WebSocket gateway implementation.
Added 2025-07-07: Command-line arguments for port override
Updated 2025-07-08: MCP server startup dependencies and health checks
"""

# Standard library imports
import argparse
import asyncio
import sys
import uvicorn

# Third-party imports
from dotenv import load_dotenv

# Local imports
from common.config import load_config
from common.logging import setup_logging, get_logger
from gateway.websocket import create_gateway_app
from mcp.mcp2025_server import get_mcp2025_server

# Load environment variables from .env file at module level
load_dotenv()

logger = get_logger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP 2025 Gateway Server")
    parser.add_argument("--port", type=int, help="Override the port to run on")
    parser.add_argument("--host", type=str, help="Override the host to run on")
    return parser.parse_args()


async def check_mcp_server_health() -> bool:
    """
    Check if MCP server is healthy and accessible.

    Returns:
        True if healthy, False otherwise
    """
    try:
        # Get MCP server instance
        mcp_server = get_mcp2025_server()

        # Try to fetch active configuration
        config = await mcp_server.get_active_provider_config()

        if not config or "provider" not in config:
            logger.error(event="mcp_health_check_failed", reason="Invalid configuration format")
            return False

        logger.info(
            event="mcp_health_check_passed",
            active_provider=config.get("provider"),
            model=config.get("model"),
        )
        return True

    except Exception as e:
        logger.error(event="mcp_health_check_failed", error=str(e))
        return False


async def validate_startup_configuration(config) -> bool:
    """
    Validate configuration at startup.

    Args:
        config: Loaded configuration

    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required configuration sections
        if not config.gateway:
            logger.error(event="config_validation_failed", reason="Missing gateway configuration")
            return False

        if not config.providers:
            logger.error(event="config_validation_failed", reason="Missing providers configuration")
            return False

        # Validate MCP server can provide configuration
        mcp_server = get_mcp2025_server()
        provider_config = await mcp_server.get_active_provider_config()

        if not provider_config:
            logger.error(
                event="config_validation_failed", reason="MCP server cannot provide configuration"
            )
            return False

        logger.info(
            event="config_validation_passed",
            gateway_host=config.gateway.host,
            gateway_port=config.gateway.port,
            active_provider=provider_config.get("provider"),
        )
        return True

    except Exception as e:
        logger.error(event="config_validation_failed", error=str(e))
        return False


async def startup_health_checks(config) -> None:
    """
    Perform all startup health checks.
    Fail fast if any critical component is unavailable.

    Args:
        config: Application configuration

    Raises:
        SystemExit: If any critical health check fails
    """
    logger.info(event="startup_health_checks_begin")

    # Check MCP server health
    logger.info(event="checking_mcp_server_health")
    if not await check_mcp_server_health():
        logger.critical(
            event="startup_failed",
            reason="MCP server health check failed",
            message="Cannot start without healthy MCP server (fail-fast policy)",
        )
        sys.exit(1)

    # Validate configuration
    logger.info(event="validating_configuration")
    if not await validate_startup_configuration(config):
        logger.critical(
            event="startup_failed",
            reason="Configuration validation failed",
            message="Invalid configuration detected (fail-fast policy)",
        )
        sys.exit(1)

    logger.info(
        event="startup_health_checks_passed", message="All startup checks passed successfully"
    )


async def run_startup_checks(config) -> None:
    """Run async startup checks."""
    logger.info(
        event="application_starting",
        version="MCP 2025 Gateway",
        host=config.gateway.host,
        port=config.gateway.port,
    )

    # Perform startup health checks (fail-fast)
    await startup_health_checks(config)


def main() -> None:
    """Main entry point."""
    try:
        # Parse arguments
        args = parse_args()

        # Load configuration
        config = load_config()

        # Setup logging
        setup_logging(config)

        # Run async startup checks
        asyncio.run(run_startup_checks(config))

        # Create FastAPI app (only after health checks pass)
        app = create_gateway_app(config)

        # Run with uvicorn (use command-line args if provided)
        host = args.host or config.gateway.host
        port = args.port or config.gateway.port

        logger.info(event="starting_server", host=host, port=port)

        # Run uvicorn synchronously (it creates its own event loop)
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_config=None,  # Use our custom logging setup
            access_log=False,  # Disable default access logs
        )

    except KeyboardInterrupt:
        logger.info(event="application_shutdown", reason="Keyboard interrupt")
    except SystemExit as e:
        if e.code == 1:
            logger.critical(event="application_failed", reason="Startup checks failed")
        else:
            logger.info(event="application_shutdown", exit_code=e.code)
    except Exception as e:
        logger.critical(event="application_crashed", error=str(e), error_type=type(e).__name__)
        sys.exit(1)


if __name__ == "__main__":
    main()
