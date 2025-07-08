"""
WebSocket gateway using FastAPI.

Main gateway orchestrator that delegates to specialized handlers.
Following PROJECT_RULES.md:
- Async/await for all I/O operations
- Timeout handling for long-running tasks
- Structured logging with elapsed_ms
- Single responsibility: WebSocket protocol handling
"""

import asyncio
import uuid
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from common.config import Config
from common.logging import TimedLogger, get_logger
from common.models import WebSocketMessage, WebSocketResponse
from gateway.connection_manager import ConnectionManager
from router.message_types import RequestType, RouterRequest
from router.request_router import RequestRouter
from mcp.mcp2025_server import get_mcp2025_server

logger = get_logger(__name__)


class WebSocketGateway:
    """FastAPI WebSocket gateway that orchestrates connections and routing."""

    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(title="Backend Gateway", version="0.1.0")
        self.connection_manager = ConnectionManager()
        # TODO: Add media handler when needed for binary/media processing
        # self.media_handler = MediaHandler(max_file_size=config.gateway.max_upload_size)

        # Initialize MCP 2025 server (single source of truth)
        self.mcp_server = get_mcp2025_server()  # MCP 2025 JSON-RPC server

        # Initialize router with MCP server dependency
        self.router = RequestRouter(config, self.mcp_server)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                # Check MCP server health
                mcp_health = await self.mcp_server.health_check()

                # Get active configuration to ensure it's working
                active_config = await self.mcp_server.get_active_provider_config()

                # Check router health (which includes adapter health)
                provider_health = await self.router.health_check_all_providers()

                overall_status = "healthy" if mcp_health else "unhealthy"

                health_data = {
                    "status": overall_status,
                    "active_connections": self.connection_manager.get_connection_count(),
                    "mcp_server": {
                        "healthy": mcp_health,
                        "active_provider": active_config.get("provider") if active_config else None,
                        "active_model": active_config.get("model") if active_config else None,
                    },
                    "providers": provider_health,
                    "message": (
                        "MCP server is the single source of truth for configuration"
                        if mcp_health
                        else "MCP server unhealthy - system cannot function"
                    ),
                }

                status_code = 200 if overall_status == "healthy" else 503
                return JSONResponse(health_data, status_code=status_code)

            except Exception as e:
                logger.error(event="health_check_failed", error=str(e))
                return JSONResponse(
                    {
                        "status": "error",
                        "error": str(e),
                        "message": "Health check failed - system may be unavailable",
                    },
                    status_code=503,
                )

        @self.app.websocket("/ws/chat")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint."""
            await self._handle_websocket_connection(websocket)

        # Include MCP 2025 server (single source of truth)
        self.app.include_router(self.mcp_server.get_router())  # JSON-RPC /mcp/* endpoints

    async def _handle_websocket_connection(self, websocket: WebSocket) -> None:
        """Handle a new WebSocket connection."""
        connection_id = str(uuid.uuid4())
        user_id = None  # TODO: Extract from authentication headers

        try:
            await self.connection_manager.connect(websocket, connection_id, user_id)

            # Handle incoming messages
            await self._message_loop(websocket, connection_id, user_id)

        except WebSocketDisconnect:
            logger.info(
                event="client_disconnect",
                message="WebSocket client disconnected",
                connection_id=connection_id,
            )
        except Exception as e:
            logger.error(
                event="connection_error",
                message="WebSocket connection error",
                connection_id=connection_id,
                error=str(e),
            )
        finally:
            self.connection_manager.disconnect(connection_id, user_id)

    async def _message_loop(
        self, websocket: WebSocket, connection_id: str, user_id: Optional[str]
    ) -> None:
        """Main message handling loop for a WebSocket connection."""
        while True:
            try:
                # Receive message with timeout
                message_data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=self.config.gateway.connection_timeout
                )

                with TimedLogger(logger, "message_processed", connection_id=connection_id):
                    await self._process_message(message_data, connection_id, user_id)

            except asyncio.TimeoutError:
                logger.warning(
                    event="connection_timeout",
                    message="WebSocket connection timeout",
                    connection_id=connection_id,
                    timeout_seconds=self.config.gateway.connection_timeout,
                )
                break
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    event="message_processing_error",
                    message="Error processing WebSocket message",
                    connection_id=connection_id,
                    error=str(e),
                )
                # Send error response to client
                error_response = WebSocketResponse(
                    request_id="error", status="error", error=f"Message processing failed: {str(e)}"
                )
                await self.connection_manager.send_to_connection(connection_id, error_response)

    async def _process_message(
        self, message_data: str, connection_id: str, user_id: Optional[str]
    ) -> None:
        """Process an incoming WebSocket message."""
        try:
            # Parse message
            message = WebSocketMessage.model_validate_json(message_data)

            logger.info(
                event="message_received",
                message="Processing WebSocket message",
                connection_id=connection_id,
                action=message.action,
                request_id=message.request_id,
            )

            # Send processing acknowledgment
            ack_response = WebSocketResponse(request_id=message.request_id, status="processing")
            await self.connection_manager.send_to_connection(connection_id, ack_response)

            # Route message to router component
            await self._route_to_router(message, connection_id, user_id)

        except Exception as e:
            logger.error(
                event="message_parse_error",
                message="Failed to parse WebSocket message",
                connection_id=connection_id,
                error=str(e),
                raw_message=message_data[:200],  # Log first 200 chars
            )
            # Send error response
            error_response = WebSocketResponse(
                request_id="parse_error", status="error", error=f"Invalid message format: {str(e)}"
            )
            await self.connection_manager.send_to_connection(connection_id, error_response)

    async def _route_to_router(
        self, message: WebSocketMessage, connection_id: str, user_id: Optional[str]
    ) -> None:
        """Route message to router and stream responses back to client."""
        try:
            # Convert WebSocket message to router request
            request_type = self._map_action_to_request_type(message.action)

            router_request = RouterRequest(
                request_id=message.request_id,
                request_type=request_type,
                payload=message.payload,
                user_id=user_id,
                connection_id=connection_id,
            )

            logger.info(
                event="router_processing_start",
                message="Starting router processing",
                connection_id=connection_id,
                request_id=message.request_id,
                request_type=request_type.value,
                payload_keys=list(message.payload.keys()) if message.payload else [],
            )

            # Process request and stream responses
            response_count = 0
            async for response in self.router.process_request(router_request):
                response_count += 1

                logger.info(
                    event="router_response_received",
                    message="Received response from router",
                    connection_id=connection_id,
                    request_id=message.request_id,
                    response_number=response_count,
                    response_status=response.status,
                )

                success = await self.connection_manager.send_to_connection(connection_id, response)

                logger.info(
                    event="router_response_forwarded",
                    message="Forwarded router response to WebSocket",
                    connection_id=connection_id,
                    request_id=message.request_id,
                    response_number=response_count,
                    send_success=success,
                )

            logger.info(
                event="router_processing_complete",
                message="Router processing completed",
                connection_id=connection_id,
                request_id=message.request_id,
                total_responses=response_count,
            )

        except Exception as e:
            logger.error(
                event="router_processing_failed",
                message="Router processing failed",
                connection_id=connection_id,
                error=str(e),
            )
            # Send error response
            error_response = WebSocketResponse(
                request_id=message.request_id,
                status="error",
                error=f"Router processing failed: {str(e)}",
            )
            await self.connection_manager.send_to_connection(connection_id, error_response)

    def _map_action_to_request_type(self, action: str) -> RequestType:
        """Map WebSocket action to router request type."""
        action_mapping = {
            "chat": RequestType.CHAT,  # Includes LLM function calling for device control
            "generate_image": RequestType.IMAGE_GENERATION,
            "audio_stream": RequestType.AUDIO_STREAM,  # TTS and audio generation
            "frontend_command": RequestType.FRONTEND_COMMAND,  # UI updates and notifications
        }

        return action_mapping.get(action, RequestType.CHAT)  # Default to chat


def create_gateway_app(config: Config) -> FastAPI:
    """Create and configure the FastAPI gateway application."""
    gateway = WebSocketGateway(config)
    return gateway.app
