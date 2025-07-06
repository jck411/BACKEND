"""
Request router for orchestrating adapter communication.

Added 2025-07-05: Core router implementation with simplified OpenAI adapter integration.
Following PROJECT_RULES.md:
- Async I/O for all operations
- Timeout handling with explicit errors
- Structured logging with elapsed_ms
- Single responsibility per class
- Future-ready for MCP integration
"""

import asyncio
from typing import Any, AsyncGenerator, Dict

from adapters.base import AdapterRequest
from adapters.openai_adapter import OpenAIAdapter
from common.config import Config
from common.logging import TimedLogger, get_logger
from common.models import Chunk, ChunkType, WebSocketResponse
from router.message_types import RequestType, RouterRequest

logger = get_logger(__name__)


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
        self.adapters: Dict[str, Any] = {}

        # Initialize OpenAI adapter
        self._initialize_adapters()

        logger.info(
            event="router_initialized",
            message="Router initialized",
            timeout=config.router.request_timeout,
            max_retries=config.router.max_retries,
        )

    def _initialize_adapters(self) -> None:
        """Initialize all configured adapters."""
        try:
            # Initialize OpenAI adapter
            openai_config = {
                "model": self.config.providers.openai_model,
                "temperature": self.config.providers.openai_temperature,
                "max_tokens": self.config.providers.openai_max_tokens,
                "system_prompt": self.config.providers.openai_system_prompt,
            }
            self.adapters["openai"] = OpenAIAdapter(openai_config)

            logger.info(
                event="adapters_initialized",
                message="Adapters initialized successfully",
                adapters=list(self.adapters.keys()),
            )
        except Exception as e:
            logger.error(
                event="adapter_initialization_failed",
                message="Failed to initialize adapters",
                error=str(e),
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
                    event="request_timeout",
                    message="Request timeout",
                    request_id=router_request.request_id,
                    timeout=self.config.router.request_timeout,
                )
                yield WebSocketResponse(
                    request_id=router_request.request_id,
                    status="error",
                    error=f"Request timeout after {self.config.router.request_timeout}s",
                )
            except Exception as e:
                logger.error(
                    event="request_failed",
                    message="Request processing failed",
                    request_id=router_request.request_id,
                    error=str(e),
                )
                yield WebSocketResponse(
                    request_id=router_request.request_id,
                    status="error",
                    error=f"Request processing failed: {str(e)}",
                )

    async def _handle_chat_request(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle chat/text generation requests."""

        text_input = request.payload.get("text", "")

        logger.info(
            event="chat_request_start",
            message="Processing chat request with OpenAI",
            request_id=request.request_id,
            input_length=len(text_input),
        )

        # Get OpenAI adapter
        openai_adapter = self.adapters.get("openai")
        if not openai_adapter:
            logger.error(
                event="openai_adapter_missing",
                message="OpenAI adapter not available",
                request_id=request.request_id,
            )
            yield WebSocketResponse(
                request_id=request.request_id,
                status="error",
                error="OpenAI adapter not available",
            )
            return

        try:
            # Prepare the adapter request
            adapter_request = AdapterRequest(
                messages=[{"role": "user", "content": text_input}],
                temperature=self.config.providers.openai_temperature,
                max_tokens=self.config.providers.openai_max_tokens,
                system_prompt=self.config.providers.openai_system_prompt,
            )

            # Stream the response
            async for adapter_response in openai_adapter.chat_completion(adapter_request):
                # Handle content streaming
                if adapter_response.content:
                    yield WebSocketResponse(
                        request_id=request.request_id,
                        status="chunk",
                        chunk=Chunk(
                            type=ChunkType.TEXT,
                            data=adapter_response.content,
                            metadata={
                                "source": "openai",
                                "model": self.config.providers.openai_model,
                                **adapter_response.metadata,
                            },
                        ),
                    )

                # Handle completion
                if adapter_response.finish_reason:
                    # Send completion
                    yield WebSocketResponse(request_id=request.request_id, status="complete")
                    break

        except Exception as e:
            logger.error(
                event="chat_request_error",
                message="Chat request processing failed",
                request_id=request.request_id,
                error=str(e),
            )
            yield WebSocketResponse(
                request_id=request.request_id,
                status="error",
                error=f"Chat processing failed: {str(e)}",
            )

    async def _handle_image_request(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle image generation requests."""

        prompt = request.payload.get("prompt", "")

        logger.info(
            event="image_request_start",
            message="Processing image request",
            request_id=request.request_id,
            prompt=prompt[:100],  # Log first 100 chars
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
            event="audio_request_start",
            message="Processing audio request",
            request_id=request.request_id,
            text_length=len(text_input),
            voice=voice,
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
            event="frontend_command_start",
            message="Processing frontend command",
            request_id=request.request_id,
            command=command,
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
        logger.info(event="router_shutdown", message="Router shutting down")

        # TODO: Cleanup adapter connections
        pass
