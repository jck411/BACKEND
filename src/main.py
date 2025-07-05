"""
Main application entry point for the backend gateway.

Added 2025-07-05: Initial FastAPI WebSocket gateway implementation.
"""

import uvicorn

from common.config import load_config
from common.logging import setup_logging
from gateway.websocket import create_gateway_app


def main() -> None:
    """Main entry point for the gateway application."""
    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(config)

    # Create FastAPI app
    app = create_gateway_app(config)

    # Run with uvicorn
    uvicorn.run(
        app,
        host=config.gateway.host,
        port=config.gateway.port,
        log_config=None,  # Use our custom logging setup
        access_log=False,  # Disable default access logs
    )


if __name__ == "__main__":
    main()
