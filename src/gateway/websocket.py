"""
WebSocket gateway using FastAPI.

Handles client connections, authentication, and message framing.
Following PROJECT_RULES.md:
- Async/await for all I/O operations
- Timeout handling for long-running tasks
- Structured logging with elapsed_ms
- Single responsibility per file
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from common.config import Config
from common.logging import TimedLogger
from common.models import WebSocketMessage, WebSocketResponse, Chunk, ChunkType
from router.message_types import RequestType, RouterRequest
from router.request_router import RequestRouter

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids

    async def connect(
        self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None
    ) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

        logger.info(
            "WebSocket connection established",
            extra={
                "event": "connection_established",
                "connection_id": connection_id,
                "user_id": user_id,
                "total_connections": len(self.active_connections),
            },
        )

    def disconnect(self, connection_id: str, user_id: Optional[str] = None) -> None:
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(
            "WebSocket connection closed",
            extra={
                "event": "connection_closed",
                "connection_id": connection_id,
                "user_id": user_id,
                "total_connections": len(self.active_connections),
            },
        )

    async def send_to_connection(self, connection_id: str, response: WebSocketResponse) -> bool:
        """
        Send a response to a specific connection.

        Returns:
            True if sent successfully, False if connection not found or failed
        """
        if connection_id not in self.active_connections:
            return False

        websocket = self.active_connections[connection_id]
        try:
            await websocket.send_text(response.model_dump_json())
            return True
        except Exception as e:
            logger.warning(
                "Failed to send message to connection",
                extra={"event": "send_failed", "connection_id": connection_id, "error": str(e)},
            )
            return False

    async def broadcast_to_user(self, user_id: str, response: WebSocketResponse) -> int:
        """
        Broadcast a response to all connections for a user.

        Returns:
            Number of connections that received the message
        """
        if user_id not in self.user_connections:
            return 0

        sent_count = 0
        for connection_id in self.user_connections[user_id]:
            if await self.send_to_connection(connection_id, response):
                sent_count += 1

        return sent_count


class WebSocketGateway:
    """FastAPI WebSocket gateway."""

    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(title="Backend Gateway", version="0.1.0")
        self.connection_manager = ConnectionManager()
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
                    "active_connections": len(self.connection_manager.active_connections),
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
                "WebSocket client disconnected",
                extra={"event": "client_disconnect", "connection_id": connection_id},
            )
        except Exception as e:
            logger.error(
                "WebSocket connection error",
                extra={
                    "event": "connection_error",
                    "connection_id": connection_id,
                    "error": str(e),
                },
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
                    "WebSocket connection timeout",
                    extra={
                        "event": "connection_timeout",
                        "connection_id": connection_id,
                        "timeout_seconds": self.config.gateway.connection_timeout,
                    },
                )
                break
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    "Error processing WebSocket message",
                    extra={
                        "event": "message_processing_error",
                        "connection_id": connection_id,
                        "error": str(e),
                    },
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
                "Processing WebSocket message",
                extra={
                    "event": "message_received",
                    "connection_id": connection_id,
                    "action": message.action,
                    "request_id": message.request_id,
                },
            )

            # Send processing acknowledgment
            ack_response = WebSocketResponse(request_id=message.request_id, status="processing")
            await self.connection_manager.send_to_connection(connection_id, ack_response)

            # Route message to router component
            await self._route_to_router(message, connection_id, user_id)

        except Exception as e:
            logger.error(
                "Failed to parse WebSocket message",
                extra={
                    "event": "message_parse_error",
                    "connection_id": connection_id,
                    "error": str(e),
                    "raw_message": message_data[:200],  # Log first 200 chars
                },
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
                "Router processing failed",
                extra={
                    "event": "router_processing_failed",
                    "connection_id": connection_id,
                    "error": str(e),
                },
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
