"""
Tests for common models and utilities.

Added 2025-07-05: Tests for data models and validation.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from common.models import ChunkType, Chunk, WebSocketMessage, WebSocketResponse


def test_chunk_type_enum():
    """Test ChunkType enum values."""
    assert ChunkType.TEXT == "text"
    assert ChunkType.IMAGE == "image"
    assert ChunkType.AUDIO == "audio"
    assert ChunkType.BINARY == "binary"
    assert ChunkType.ERROR == "error"
    assert ChunkType.METADATA == "metadata"


def test_chunk_creation():
    """Test Chunk model creation and validation."""
    chunk = Chunk(
        type=ChunkType.TEXT,
        data="Hello, world!",
        metadata={"source": "test"},
        sequence_id="seq-123",
    )

    assert chunk.type == ChunkType.TEXT
    assert chunk.data == "Hello, world!"
    assert chunk.metadata["source"] == "test"
    assert chunk.sequence_id == "seq-123"
    assert isinstance(chunk.timestamp, datetime)


def test_chunk_with_binary_data():
    """Test Chunk with binary data."""
    binary_data = b"binary content"
    chunk = Chunk(type=ChunkType.BINARY, data=binary_data, metadata={"format": "mp3"})

    assert chunk.type == ChunkType.BINARY
    assert chunk.data == binary_data
    assert chunk.metadata["format"] == "mp3"


def test_websocket_message_creation():
    """Test WebSocketMessage model creation and validation."""
    message = WebSocketMessage(
        action="chat", payload={"text": "Hello"}, request_id="req-123", user_id="user-456"
    )

    assert message.action == "chat"
    assert message.payload["text"] == "Hello"
    assert message.request_id == "req-123"
    assert message.user_id == "user-456"


def test_websocket_message_validation():
    """Test WebSocketMessage validation."""
    with pytest.raises(ValidationError):
        # Missing required fields
        WebSocketMessage(action="chat", request_id="missing")

    # Valid minimal message
    message = WebSocketMessage(action="chat", request_id="req-123")
    assert message.payload == {}
    assert message.user_id is None


def test_websocket_response_with_chunk():
    """Test WebSocketResponse with chunk data."""
    chunk = Chunk(type=ChunkType.TEXT, data="Response text")

    response = WebSocketResponse(request_id="req-123", status="chunk", chunk=chunk)

    assert response.request_id == "req-123"
    assert response.status == "chunk"
    assert response.chunk is not None
    assert response.chunk.type == ChunkType.TEXT
    assert response.chunk.data == "Response text"
    assert response.error is None


def test_websocket_response_with_error():
    """Test WebSocketResponse with error."""
    response = WebSocketResponse(request_id="req-123", status="error", error="Something went wrong")

    assert response.request_id == "req-123"
    assert response.status == "error"
    assert response.error == "Something went wrong"
    assert response.chunk is None


def test_websocket_response_serialization():
    """Test WebSocketResponse JSON serialization."""
    chunk = Chunk(type=ChunkType.METADATA, data="metadata info")
    response = WebSocketResponse(request_id="req-123", status="chunk", chunk=chunk)

    json_data = response.model_dump_json()
    assert isinstance(json_data, str)
    assert "req-123" in json_data
    assert "metadata info" in json_data


def test_action_descriptions():
    """Test that action descriptions are properly defined."""
    # Test that the action field has proper description
    message_fields = WebSocketMessage.model_fields
    action_field = message_fields["action"]

    assert action_field.description is not None
    assert "chat" in action_field.description
    assert "audio_stream" in action_field.description
    assert "frontend_command" in action_field.description


def test_audio_chunk_metadata():
    """Test audio chunk with proper metadata."""
    audio_chunk = Chunk(
        type=ChunkType.AUDIO,
        data="simulated_audio_data",
        metadata={"sample_rate": 22050, "format": "mp3", "duration": 5.2, "voice": "en-US-female"},
    )

    assert audio_chunk.type == ChunkType.AUDIO
    assert audio_chunk.metadata["sample_rate"] == 22050
    assert audio_chunk.metadata["format"] == "mp3"
    assert audio_chunk.metadata["duration"] == 5.2


def test_complex_payload_structures():
    """Test complex payload structures in WebSocket messages."""
    # Image generation request
    image_message = WebSocketMessage(
        action="generate_image",
        payload={
            "prompt": "A beautiful sunset over mountains",
            "style": "photorealistic",
            "size": "1024x1024",
            "quality": "high",
            "parameters": {"steps": 50, "cfg_scale": 7.5},
        },
        request_id="img-req-123",
    )

    assert image_message.action == "generate_image"
    assert image_message.payload["prompt"] == "A beautiful sunset over mountains"
    assert image_message.payload["parameters"]["steps"] == 50

    # Frontend command request
    frontend_message = WebSocketMessage(
        action="frontend_command",
        payload={
            "command": "show_notification",
            "data": {
                "title": "Device Status",
                "message": "Lights turned on successfully",
                "type": "success",
                "duration": 3000,
            },
        },
        request_id="cmd-req-456",
    )

    assert frontend_message.action == "frontend_command"
    assert frontend_message.payload["command"] == "show_notification"
    assert frontend_message.payload["data"]["type"] == "success"
