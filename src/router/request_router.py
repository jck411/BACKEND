"""
Request router for orchestrating adapter communication.

Added 2025-07-05: Core router implementation.
Following PROJECT_RULES.md:
- Async I/O for all operations
- Timeout handling with explicit errors
- Structured logging with elapsed_ms
- Single responsibility per class
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict

from common.config import Config
from common.logging import TimedLogger
from common.models import Chunk, ChunkType, WebSocketResponse
from router.message_types import RequestType, RouterRequest

logger = logging.getLogger(__name__)


class RequestRouter:
    """
    Core router for handling requests and orchestrating adapters.

    Responsibilities:
    - Route requests based on type
    - Handle timeouts and retries
    - Stream responses back to gateway
    - Manage adapter lifecycle
    """

    def __init__(self, config: Config):
        self.config = config
        self.adapters: Dict[str, Any] = {}  # Will hold adapter instances

        logger.info(
            "Router initialized",
            extra={
                "event": "router_initialized",
                "timeout": config.router.request_timeout,
                "max_retries": config.router.max_retries,
            },
        )

    async def process_request(
        self, router_request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """
        Process a request and yield streaming responses.

        Args:
            router_request: The request to process

        Yields:
            WebSocketResponse objects for streaming back to client
        """
        with TimedLogger(
            logger,
            "request_processed",
            request_id=router_request.request_id,
            request_type=router_request.request_type.value,
        ):
            try:
                # Route based on request type
                if router_request.request_type == RequestType.CHAT:
                    async for response in self._handle_chat_request(router_request):
                        yield response
                elif router_request.request_type == RequestType.IMAGE_GENERATION:
                    async for response in self._handle_image_request(router_request):
                        yield response
                elif router_request.request_type == RequestType.AUDIO_STREAM:
                    async for response in self._handle_audio_request(router_request):
                        yield response
                elif router_request.request_type == RequestType.FRONTEND_COMMAND:
                    async for response in self._handle_frontend_command(router_request):
                        yield response
                else:
                    # Unknown request type
                    yield WebSocketResponse(
                        request_id=router_request.request_id,
                        status="error",
                        error=f"Unknown request type: {router_request.request_type}",
                    )

            except asyncio.TimeoutError:
                logger.warning(
                    "Request timeout",
                    extra={
                        "event": "request_timeout",
                        "request_id": router_request.request_id,
                        "timeout": self.config.router.request_timeout,
                    },
                )
                yield WebSocketResponse(
                    request_id=router_request.request_id,
                    status="error",
                    error=f"Request timeout after {self.config.router.request_timeout}s",
                )
            except Exception as e:
                logger.error(
                    "Request processing failed",
                    extra={
                        "event": "request_failed",
                        "request_id": router_request.request_id,
                        "error": str(e),
                    },
                )
                yield WebSocketResponse(
                    request_id=router_request.request_id,
                    status="error",
                    error=f"Request processing failed: {str(e)}",
                )

    async def _handle_chat_request(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle chat/text generation requests with potential device control via function calling."""

        # For now, simulate AI response generation with function calling capability
        # TODO: Route to actual AI adapter (OpenAI, Anthropic, etc.) with function calling

        text_input = request.payload.get("text", "")

        logger.info(
            "Processing chat request",
            extra={
                "event": "chat_request_start",
                "request_id": request.request_id,
                "input_length": len(text_input),
            },
        )

        # Check if request might involve device control
        device_keywords = ["light", "turn on", "turn off", "device", "temperature", "thermostat"]
        has_device_intent = any(keyword in text_input.lower() for keyword in device_keywords)

        # Simulate streaming AI response with potential function calling
        responses = [
            "I understand you're asking about: ",
            f'"{text_input[:50]}..." ',
        ]

        if has_device_intent:
            responses.extend(
                [
                    "I detected a device control request. ",
                    "Executing device function via LLM function calling... ",
                    "✅ Device control completed successfully. ",
                ]
            )
        else:
            responses.extend(
                [
                    "This is a simulated chat response from the router. ",
                    "In the future, this will connect to real AI adapters ",
                    "with function calling capabilities for device control.",
                ]
            )

        for i, response_text in enumerate(responses):
            # Add artificial delay to simulate real AI streaming
            await asyncio.sleep(0.2)

            yield WebSocketResponse(
                request_id=request.request_id,
                status="chunk",
                chunk=Chunk(
                    type=ChunkType.TEXT,
                    data=response_text,
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(responses),
                        "source": "router_simulation",
                        "has_function_call": has_device_intent and i >= 2,
                    },
                ),
            )

        # Send completion
        yield WebSocketResponse(request_id=request.request_id, status="complete")

    async def _handle_image_request(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle image generation requests."""

        prompt = request.payload.get("prompt", "")

        logger.info(
            "Processing image request",
            extra={
                "event": "image_request_start",
                "request_id": request.request_id,
                "prompt": prompt[:100],  # Log first 100 chars
            },
        )

        # Simulate image generation delay
        await asyncio.sleep(1.0)

        yield WebSocketResponse(
            request_id=request.request_id,
            status="chunk",
            chunk=Chunk(
                type=ChunkType.TEXT,
                data=f"🎨 Simulated image generation for prompt: '{prompt}'",
                metadata={"source": "router_simulation", "type": "image_placeholder"},
            ),
        )

        yield WebSocketResponse(request_id=request.request_id, status="complete")

    async def _handle_audio_request(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle audio streaming requests (TTS, etc.)."""

        text_input = request.payload.get("text", "")
        voice = request.payload.get("voice", "en-US-default")

        logger.info(
            "Processing audio request",
            extra={
                "event": "audio_request_start",
                "request_id": request.request_id,
                "text_length": len(text_input),
                "voice": voice,
            },
        )

        # Simulate TTS processing delay
        await asyncio.sleep(0.8)

        # Send metadata about audio generation
        yield WebSocketResponse(
            request_id=request.request_id,
            status="chunk",
            chunk=Chunk(
                type=ChunkType.METADATA,
                data=f"🔊 Generating audio for voice: {voice}",
                metadata={
                    "source": "router_simulation",
                    "voice": voice,
                    "text_length": len(text_input),
                    "estimated_duration": len(text_input) * 0.05,  # rough estimate
                },
            ),
        )

        # Simulate audio data chunks (in real implementation, this would be actual audio data)
        audio_chunks = ["chunk1_base64", "chunk2_base64", "chunk3_base64"]
        for i, chunk_data in enumerate(audio_chunks):
            await asyncio.sleep(0.3)
            yield WebSocketResponse(
                request_id=request.request_id,
                status="chunk",
                chunk=Chunk(
                    type=ChunkType.BINARY,
                    data=f"simulated_audio_data_{i}",
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(audio_chunks),
                        "audio_format": "mp3",
                        "sample_rate": 22050,
                    },
                ),
            )

        yield WebSocketResponse(request_id=request.request_id, status="complete")

    async def _handle_frontend_command(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle frontend-specific commands (notifications, UI updates)."""

        command = request.payload.get("command", "unknown")
        data = request.payload.get("data", {})

        logger.info(
            "Processing frontend command",
            extra={
                "event": "frontend_command_start",
                "request_id": request.request_id,
                "command": command,
            },
        )

        # Simulate frontend command processing
        await asyncio.sleep(0.1)

        yield WebSocketResponse(
            request_id=request.request_id,
            status="chunk",
            chunk=Chunk(
                type=ChunkType.METADATA,
                data=f"📱 Executing frontend command: {command}",
                metadata={"source": "router_simulation", "command": command, "command_data": data},
            ),
        )

        yield WebSocketResponse(request_id=request.request_id, status="complete")

    async def shutdown(self) -> None:
        """Gracefully shutdown the router and cleanup resources."""
        logger.info("Router shutting down", extra={"event": "router_shutdown"})

        # TODO: Cleanup adapter connections
        pass
