"""
WebSocket connection management.

Handles connection lifecycle, user mapping, and message broadcasting.
Following PROJECT_RULES.md:
- Single responsibility: connection management only
- Structured logging with elapsed_ms
- Async I/O for all operations
"""

from typing import Dict, Optional, Set

from fastapi import WebSocket

from common.logging import get_logger
from common.models import WebSocketResponse

logger = get_logger(__name__)


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
            event="connection_established",
            message="WebSocket connection established",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self.active_connections),
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
            event="connection_closed",
            message="WebSocket connection closed",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self.active_connections),
        )

    async def send_to_connection(self, connection_id: str, response: WebSocketResponse) -> bool:
        """
        Send a response to a specific connection.

        Returns:
            True if sent successfully, False if connection not found or failed
        """
        # Log what we're trying to send
        logger.info(
            event="websocket_send_attempt",
            message="Attempting to send WebSocket response",
            connection_id=connection_id,
            response_status=response.status,
            request_id=response.request_id,
            has_chunk=bool(response.chunk),
            chunk_type=response.chunk.type.value if response.chunk else None,
            chunk_data_length=(
                len(response.chunk.data) if response.chunk and response.chunk.data else 0
            ),
            has_error=bool(response.error),
        )

        if connection_id not in self.active_connections:
            logger.error(
                event="connection_not_found",
                message="Connection not found for send attempt",
                connection_id=connection_id,
                request_id=response.request_id,
                active_connections=list(self.active_connections.keys()),
            )
            return False

        websocket = self.active_connections[connection_id]
        try:
            response_json = response.model_dump_json()

            logger.info(
                event="websocket_sending",
                message="Sending WebSocket message",
                connection_id=connection_id,
                request_id=response.request_id,
                json_length=len(response_json),
                json_preview=(
                    response_json[:200] + "..." if len(response_json) > 200 else response_json
                ),
            )

            await websocket.send_text(response_json)

            logger.info(
                event="websocket_sent_successfully",
                message="WebSocket message sent successfully",
                connection_id=connection_id,
                request_id=response.request_id,
            )

            return True
        except Exception as e:
            logger.error(
                event="send_failed",
                message="Failed to send message to connection",
                connection_id=connection_id,
                request_id=response.request_id,
                error=str(e),
                error_type=type(e).__name__,
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

    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self.active_connections)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of connections for a specific user."""
        return len(self.user_connections.get(user_id, set()))
