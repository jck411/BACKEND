"""
Test for the WebSocket gateway.

Added 2025-07-05: Basic test for FastAPI WebSocket functionality.
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


def test_health_endpoint(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_connections" in data


def test_websocket_connection(client: TestClient) -> None:
    """Test basic WebSocket connection."""
    with client.websocket_connect("/ws") as websocket:
        # Should receive welcome message
        data = websocket.receive_text()
        response = json.loads(data)
        
        assert response["request_id"] == "welcome"
        assert response["status"] == "complete"
        assert response["chunk"]["type"] == "metadata"


def test_websocket_message_handling(client: TestClient) -> None:
    """Test WebSocket message processing."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_text()
        
        # Send a test message
        test_message = WebSocketMessage(
            action="chat",
            payload={"text": "Hello, world!"},
            request_id="test-123"
        )
        websocket.send_text(test_message.model_dump_json())
        
        # Should receive processing acknowledgment
        ack_data = websocket.receive_text()
        ack_response = json.loads(ack_data)
        assert ack_response["request_id"] == "test-123"
        assert ack_response["status"] == "processing"
        
        # Should receive mock chunks
        chunk_count = 0
        while True:
            data = websocket.receive_text()
            response = json.loads(data)
            
            if response["status"] == "complete":
                break
            elif response["status"] == "chunk":
                chunk_count += 1
                assert response["chunk"]["type"] == "text"
                assert "Mock response chunk" in response["chunk"]["data"]
        
        assert chunk_count == 3  # Should receive 3 mock chunks


def test_invalid_message_format(client: TestClient) -> None:
    """Test handling of invalid message format."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_text()
        
        # Send invalid JSON
        websocket.send_text("invalid json")
        
        # Should receive error response
        data = websocket.receive_text()
        response = json.loads(data)
        assert response["request_id"] == "parse_error"
        assert response["status"] == "error"
        assert "Invalid message format" in response["error"]
