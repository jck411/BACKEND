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
from common.models import WebSocketMessage, WebSocketResponse, Chunk, ChunkType
from gateway.connection_manager import ConnectionManager
from router.message_types import RequestType, RouterRequest
from router.request_router import RequestRouter

logger = get_logger(__name__)


class WebSocketGateway:
    """FastAPI WebSocket gateway that orchestrates connections and routing."""

    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(title="Backend Gateway", version="0.1.0")
        self.connection_manager = ConnectionManager()
        # TODO: Add media handler when needed for binary/media processing
        # self.media_handler = MediaHandler(max_file_size=config.gateway.max_upload_size)
        self.router = RequestRouter(config)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return JSONResponse(
                {
                    "status": "healthy",
                    "active_connections": self.connection_manager.get_connection_count(),
                }
            )

        @self.app.websocket("/ws/chat")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint."""
            await self._handle_websocket_connection(websocket)

    async def _handle_websocket_connection(self, websocket: WebSocket) -> None:
        """Handle a new WebSocket connection."""
        connection_id = str(uuid.uuid4())
        user_id = None  # TODO: Extract from authentication headers

        try:
            await self.connection_manager.connect(websocket, connection_id, user_id)

            # Send welcome message
            welcome_response = WebSocketResponse(
                request_id="welcome",
                status="complete",
                chunk=Chunk(
                    type=ChunkType.METADATA,
                    data=f"Connected with ID: {connection_id}",
                    metadata={"connection_id": connection_id},
                ),
            )
            await self.connection_manager.send_to_connection(connection_id, welcome_response)

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

            # Process request and stream responses
            async for response in self.router.process_request(router_request):
                await self.connection_manager.send_to_connection(connection_id, response)

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
