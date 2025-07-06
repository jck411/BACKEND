"""
Integration tests for WebSocket functionality.

Added 2025-07-05: End-to-end tests for WebSocket protocol.
"""

import json
import pytest
from fastapi.testclient import TestClient

from common.config import Config
from common.models import WebSocketMessage
from gateway.websocket import create_gateway_app


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    return Config()


@pytest.fixture
def app(test_config: Config):
    """Create a test FastAPI app."""
    return create_gateway_app(test_config)


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_audio_stream_protocol(client: TestClient) -> None:
    """Test audio streaming protocol."""
    with client.websocket_connect("/ws/chat") as websocket:
        # Skip welcome message
        websocket.receive_text()

        # Send audio stream request
        audio_message = WebSocketMessage(
            action="audio_stream",
            payload={
                "text": "Hello, this is a test message for TTS",
                "voice": "en-US-female",
                "speed": 1.0,
            },
            request_id="audio-test-123",
        )
        websocket.send_text(audio_message.model_dump_json())

        # Should receive processing acknowledgment
        ack_data = websocket.receive_text()
        ack_response = json.loads(ack_data)
        assert ack_response["request_id"] == "audio-test-123"
        assert ack_response["status"] == "processing"

        # Should receive audio-related chunks
        metadata_received = False
        binary_received = False

        while True:
            data = websocket.receive_text()
            response = json.loads(data)

            if response["status"] == "complete":
                break
            elif response["status"] == "chunk":
                chunk = response["chunk"]
                if chunk["type"] == "metadata" and "audio" in chunk["data"].lower():
                    metadata_received = True
                elif chunk["type"] == "binary":
                    binary_received = True

        # Should have received both metadata and binary chunks
        assert metadata_received, "Should receive metadata about audio generation"
        assert binary_received, "Should receive binary audio data"


def test_frontend_command_protocol(client: TestClient) -> None:
    """Test frontend command protocol."""
    with client.websocket_connect("/ws/chat") as websocket:
        # Skip welcome message
        websocket.receive_text()

        # Send frontend command request
        command_message = WebSocketMessage(
            action="frontend_command",
            payload={
                "command": "show_notification",
                "data": {
                    "title": "Test Notification",
                    "message": "This is a test notification",
                    "type": "info",
                },
            },
            request_id="cmd-test-456",
        )
        websocket.send_text(command_message.model_dump_json())

        # Should receive processing acknowledgment
        ack_data = websocket.receive_text()
        ack_response = json.loads(ack_data)
        assert ack_response["request_id"] == "cmd-test-456"
        assert ack_response["status"] == "processing"

        # Should receive command execution response
        command_executed = False

        while True:
            data = websocket.receive_text()
            response = json.loads(data)

            if response["status"] == "complete":
                break
            elif response["status"] == "chunk":
                chunk = response["chunk"]
                if chunk["type"] == "metadata" and "frontend command" in chunk["data"].lower():
                    command_executed = True

        assert command_executed, "Should receive confirmation of frontend command execution"


def test_device_control_via_chat(client: TestClient) -> None:
    """Test chat response to device control requests (functionality pending MCP implementation)."""
    with client.websocket_connect("/ws/chat") as websocket:
        # Skip welcome message
        websocket.receive_text()

        # Send chat request with device control intent
        chat_message = WebSocketMessage(
            action="chat",
            payload={
                "text": "Please turn on the living room lights and set temperature to 72 degrees"
            },
            request_id="device-chat-789",
        )
        websocket.send_text(chat_message.model_dump_json())

        # Should receive processing acknowledgment
        ack_data = websocket.receive_text()
        ack_response = json.loads(ack_data)
        assert ack_response["request_id"] == "device-chat-789"
        assert ack_response["status"] == "processing"

        # Should receive chat response (device control functionality will be added via MCP later)
        received_chunks = False
        completed = False

        while True:
            data = websocket.receive_text()
            response = json.loads(data)

            if response["status"] == "complete":
                completed = True
                break
            elif response["status"] == "chunk":
                received_chunks = True
                chunk = response["chunk"]
                # Verify we get valid chunk structure
                assert "data" in chunk
                assert chunk["type"] == "text"
                # Should have metadata indicating the source provider
                metadata = chunk.get("metadata", {})
                assert "source" in metadata

        assert received_chunks, "Should receive streaming chat chunks"
        assert completed, "Should complete the request"


def test_image_generation_protocol(client: TestClient) -> None:
    """Test image generation protocol."""
    with client.websocket_connect("/ws/chat") as websocket:
        # Skip welcome message
        websocket.receive_text()

        # Send image generation request
        image_message = WebSocketMessage(
            action="generate_image",
            payload={
                "prompt": "A beautiful sunset over mountains",
                "style": "photorealistic",
                "size": "1024x1024",
            },
            request_id="img-test-101",
        )
        websocket.send_text(image_message.model_dump_json())

        # Should receive processing acknowledgment
        ack_data = websocket.receive_text()
        ack_response = json.loads(ack_data)
        assert ack_response["request_id"] == "img-test-101"
        assert ack_response["status"] == "processing"

        # Should receive image generation response
        image_response_received = False

        while True:
            data = websocket.receive_text()
            response = json.loads(data)

            if response["status"] == "complete":
                break
            elif response["status"] == "chunk":
                chunk = response["chunk"]
                if "image" in chunk["data"].lower():
                    image_response_received = True

        assert image_response_received, "Should receive image generation response"


def test_malformed_action_handling(client: TestClient) -> None:
    """Test handling of unknown action types."""
    with client.websocket_connect("/ws/chat") as websocket:
        # Skip welcome message
        websocket.receive_text()

        # Send request with unknown action
        unknown_message = WebSocketMessage(
            action="unknown_action", payload={"test": "data"}, request_id="unknown-123"
        )
        websocket.send_text(unknown_message.model_dump_json())

        # Should receive processing acknowledgment
        ack_data = websocket.receive_text()
        ack_response = json.loads(ack_data)
        assert ack_response["request_id"] == "unknown-123"
        assert ack_response["status"] == "processing"

        # Should handle unknown action gracefully (defaults to chat)
        response_received = False
        while True:
            data = websocket.receive_text()
            response = json.loads(data)

            if response["status"] == "complete":
                response_received = True
                break
            elif response["status"] == "error":
                # Could also be an error, which is acceptable
                response_received = True
                break

        assert response_received, "Should handle unknown actions gracefully"


def test_connection_management(client: TestClient) -> None:
    """Test WebSocket connection management."""
    # Test multiple connections
    with client.websocket_connect("/ws/chat") as ws1:
        with client.websocket_connect("/ws/chat") as ws2:
            # Both should receive welcome messages
            welcome1 = json.loads(ws1.receive_text())
            welcome2 = json.loads(ws2.receive_text())

            assert welcome1["request_id"] == "welcome"
            assert welcome2["request_id"] == "welcome"
            assert (
                welcome1["chunk"]["metadata"]["connection_id"]
                != welcome2["chunk"]["metadata"]["connection_id"]
            )

            # Both connections should work independently
            test_msg = WebSocketMessage(
                action="chat", payload={"text": "test"}, request_id="multi-test"
            )

            ws1.send_text(test_msg.model_dump_json())
            ws2.send_text(test_msg.model_dump_json())

            # Both should receive acknowledgments
            ack1 = json.loads(ws1.receive_text())
            ack2 = json.loads(ws2.receive_text())

            assert ack1["status"] == "processing"
            assert ack2["status"] == "processing"
