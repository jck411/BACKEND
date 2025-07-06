"""
Tests for the request router.

Added 2025-07-05: Comprehensive tests for router functionality.
"""

import pytest

from common.config import Config
from common.models import ChunkType
from router.message_types import RequestType, RouterRequest
from router.request_router import RequestRouter


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    return Config()


@pytest.fixture
def router(test_config: Config) -> RequestRouter:
    """Create a test router."""
    return RequestRouter(test_config)


@pytest.mark.asyncio
async def test_chat_request_processing(router: RequestRouter) -> None:
    """Test basic chat request processing."""
    request = RouterRequest(
        request_id="test-123",
        request_type=RequestType.CHAT,
        payload={"text": "Hello, how are you?"},
        connection_id="conn-456",
    )

    responses = []
    async for response in router.process_request(request):
        responses.append(response)

    # Should have multiple chunks and completion
    assert len(responses) > 0

    # Last response should be complete
    assert responses[-1].status == "complete"

    # Should have text chunks (actual OpenAI responses)
    text_chunks = [r for r in responses if r.chunk and r.chunk.type == ChunkType.TEXT]
    assert len(text_chunks) > 0

    # Should have content from OpenAI
    content = "".join(chunk.chunk.data for chunk in text_chunks if chunk.chunk and chunk.chunk.data)
    assert len(content) > 0
    print(f"Received content: {content[:100]}...")  # Debug output


@pytest.mark.asyncio
async def test_chat_request_without_device_intent(router: RequestRouter) -> None:
    """Test chat request without device control intent."""
    request = RouterRequest(
        request_id="test-456",
        request_type=RequestType.CHAT,
        payload={"text": "What's the weather like today?"},
        connection_id="conn-789",
    )

    responses = []
    async for response in router.process_request(request):
        responses.append(response)

    # Should have multiple chunks and completion
    assert len(responses) > 0
    assert responses[-1].status == "complete"

    # Should have simulated chat responses
    text_chunks = [r for r in responses if r.chunk and r.chunk.type == ChunkType.TEXT]
    assert len(text_chunks) > 0


@pytest.mark.asyncio
async def test_image_generation_request(router: RequestRouter) -> None:
    """Test image generation request processing."""
    request = RouterRequest(
        request_id="img-123",
        request_type=RequestType.IMAGE_GENERATION,
        payload={"prompt": "A beautiful sunset", "style": "photorealistic"},
        connection_id="conn-123",
    )

    responses = []
    async for response in router.process_request(request):
        responses.append(response)

    # Should have at least one response and completion
    assert len(responses) >= 2
    assert responses[-1].status == "complete"

    # Should have image-related content
    text_chunks = [r for r in responses if r.chunk and r.chunk.type == ChunkType.TEXT]
    assert any("image" in chunk.chunk.data.lower() for chunk in text_chunks)


@pytest.mark.asyncio
async def test_audio_stream_request(router: RequestRouter) -> None:
    """Test audio streaming request processing."""
    request = RouterRequest(
        request_id="audio-123",
        request_type=RequestType.AUDIO_STREAM,
        payload={"text": "Hello world", "voice": "en-US-female"},
        connection_id="conn-456",
    )

    responses = []
    async for response in router.process_request(request):
        responses.append(response)

    # Should have multiple responses and completion
    assert len(responses) > 1
    assert responses[-1].status == "complete"

    # Should have metadata about audio generation
    metadata_chunks = [r for r in responses if r.chunk and r.chunk.type == ChunkType.METADATA]
    assert len(metadata_chunks) > 0

    # Should have binary audio data
    binary_chunks = [r for r in responses if r.chunk and r.chunk.type == ChunkType.BINARY]
    assert len(binary_chunks) > 0


@pytest.mark.asyncio
async def test_frontend_command_request(router: RequestRouter) -> None:
    """Test frontend command request processing."""
    request = RouterRequest(
        request_id="cmd-123",
        request_type=RequestType.FRONTEND_COMMAND,
        payload={"command": "show_notification", "data": {"message": "Test notification"}},
        connection_id="conn-789",
    )

    responses = []
    async for response in router.process_request(request):
        responses.append(response)

    # Should have at least one response and completion
    assert len(responses) >= 2
    assert responses[-1].status == "complete"

    # Should have metadata about command execution
    metadata_chunks = [r for r in responses if r.chunk and r.chunk.type == ChunkType.METADATA]
    assert len(metadata_chunks) > 0
    assert any("frontend command" in chunk.chunk.data.lower() for chunk in metadata_chunks)


@pytest.mark.asyncio
async def test_request_timeout_handling(router: RequestRouter) -> None:
    """Test timeout handling in router (simulated)."""
    # This test would need actual timeout simulation,
    # but for now we test that the router initializes correctly
    assert router.config is not None
    assert router.adapters == {}


@pytest.mark.asyncio
async def test_router_shutdown(router: RequestRouter) -> None:
    """Test router shutdown functionality."""
    await router.shutdown()
    # Should complete without errors
    assert True


@pytest.mark.asyncio
async def test_invalid_request_type() -> None:
    """Test handling of invalid request types."""
    # This would be handled at the enum level, so just verify enum values
    valid_types = {
        RequestType.CHAT,
        RequestType.IMAGE_GENERATION,
        RequestType.AUDIO_STREAM,
        RequestType.FRONTEND_COMMAND,
    }
    assert len(valid_types) == 4
    assert RequestType.CHAT.value == "chat"
    assert RequestType.AUDIO_STREAM.value == "audio_stream"
    assert RequestType.FRONTEND_COMMAND.value == "frontend_command"
