"""
Request router for orchestrating adapter communication.

Added 2025-07-05: Core router implementation with simplified OpenAI adapter integration.
Updated 2025-07-06: Multi-provider support with strict mode (no fallbacks).
Updated 2025-07-07: MCP integration for self-configuration capabilities.
Following PROJECT_RULES.md:
- Async I/O for all operations
- Timeout handling with explicit errors
- Structured logging with elapsed_ms
- Single responsibility per class
- Future-ready for MCP integration
"""

import asyncio
import os
from typing import AsyncGenerator, Dict

from adapters.base import AdapterRequest, BaseAdapter
from adapters.openai_adapter import OpenAIAdapter
from common.config import Config
from common.runtime_config import get_active_provider_config, get_runtime_config_manager
from common.logging import TimedLogger, get_logger
from common.models import Chunk, ChunkType, WebSocketResponse
from router.message_types import RequestType, RouterRequest
from mcp.connection_manager import MCPConnectionManager

# Import other adapters with fallback handling
try:
    from adapters.anthropic_adapter import AnthropicAdapter
except ImportError:
    AnthropicAdapter = None

try:
    from adapters.gemini_adapter import GeminiAdapter
except ImportError:
    GeminiAdapter = None

try:
    from adapters.openrouter_adapter import OpenRouterAdapter
except ImportError:
    OpenRouterAdapter = None

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
        self.adapters: Dict[str, BaseAdapter] = {}

        # Initialize runtime config manager and MCP
        self.runtime_config_manager = get_runtime_config_manager()
        self.mcp_manager = MCPConnectionManager(self.runtime_config_manager)

        # Initialize all available adapters
        self._initialize_adapters()

        logger.info(
            event="router_initialized",
            message="Router initialized with MCP support",
            timeout=config.router.request_timeout,
            max_retries=config.router.max_retries,
            available_providers=list(self.adapters.keys()),
            active_provider=config.providers.active,
            mcp_capabilities=list(self.mcp_manager.capabilities.keys()),
        )

    def _initialize_adapters(self) -> None:
        """Initialize all available adapters based on environment variables."""
        # Note: These configurations are temporary and will move to MCP service later

        try:
            # Initialize OpenAI adapter
            if os.getenv("OPENAI_API_KEY"):
                openai_config = {
                    "model": self.config.providers.openai_model,
                    "temperature": self.config.providers.openai_temperature,
                    "max_tokens": self.config.providers.openai_max_tokens,
                    "system_prompt": self.config.providers.openai_system_prompt,
                }
                self.adapters["openai"] = OpenAIAdapter(openai_config)
                logger.info(event="openai_adapter_loaded", message="OpenAI adapter initialized")

            # Initialize Anthropic adapter
            if os.getenv("ANTHROPIC_API_KEY") and AnthropicAdapter is not None:
                anthropic_config = {
                    "model": self.config.providers.anthropic_model,
                    "temperature": self.config.providers.anthropic_temperature,
                    "max_tokens": self.config.providers.anthropic_max_tokens,
                    "system_prompt": self.config.providers.anthropic_system_prompt,
                }
                self.adapters["anthropic"] = AnthropicAdapter(anthropic_config)
                logger.info(
                    event="anthropic_adapter_loaded", message="Anthropic adapter initialized"
                )

            # Initialize Gemini adapter
            if os.getenv("GEMINI_API_KEY") and GeminiAdapter is not None:
                gemini_config = {
                    "model": self.config.providers.gemini_model,
                    "temperature": self.config.providers.gemini_temperature,
                    "max_tokens": self.config.providers.gemini_max_tokens,
                    "system_prompt": self.config.providers.gemini_system_prompt,
                }
                self.adapters["gemini"] = GeminiAdapter(gemini_config)
                logger.info(event="gemini_adapter_loaded", message="Gemini adapter initialized")

            # Initialize OpenRouter adapter
            if os.getenv("OPENROUTER_API_KEY") and OpenRouterAdapter is not None:
                openrouter_config = {
                    "model": self.config.providers.openrouter_model,
                    "temperature": self.config.providers.openrouter_temperature,
                    "max_tokens": self.config.providers.openrouter_max_tokens,
                    "system_prompt": self.config.providers.openrouter_system_prompt,
                }
                self.adapters["openrouter"] = OpenRouterAdapter(openrouter_config)
                logger.info(
                    event="openrouter_adapter_loaded", message="OpenRouter adapter initialized"
                )

            # Ensure we have at least one adapter available
            if not self.adapters:
                raise ValueError(
                    "No AI providers available. Please set at least one API key: "
                    "OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY"
                )

            logger.info(
                event="adapters_initialized",
                message="Adapters initialized successfully",
                adapters=list(self.adapters.keys()),
                total_adapters=len(self.adapters),
            )
        except Exception as e:
            logger.error(
                event="adapter_initialization_failed",
                message="Failed to initialize adapters",
                error=str(e),
            )
            raise

    def _get_active_adapter(self) -> BaseAdapter:
        """Get the active adapter based on runtime configuration (strict mode - no fallbacks)."""
        # Get runtime config for active provider
        runtime_config = get_active_provider_config()
        active_provider = runtime_config["provider"]

        # Strict mode: fail fast if provider not available
        if active_provider not in self.adapters:
            raise ValueError(
                f"Active provider '{active_provider}' not available. "
                f"Available providers: {list(self.adapters.keys())}. "
                f"Check your API keys and runtime_config.yaml settings."
            )

        logger.info(
            event="active_provider_selected",
            message="Active provider selected",
            provider=active_provider,
            model=runtime_config["model"],
        )

        return self.adapters[active_provider]

    async def health_check_all_providers(self) -> Dict[str, bool]:
        """Check health of all configured providers."""
        health_status = {}

        for name, adapter in self.adapters.items():
            try:
                health_status[name] = await adapter.health_check()
                logger.info(
                    event="provider_health_check",
                    provider=name,
                    healthy=health_status[name],
                )
            except Exception as e:
                logger.error(
                    event="provider_health_check_failed",
                    provider=name,
                    error=str(e),
                )
                health_status[name] = False

        return health_status

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
                elif router_request.request_type == RequestType.MCP_REQUEST:
                    async for response in self._handle_mcp_request(router_request):
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

        # Get active adapter with fallback logic
        try:
            active_adapter = self._get_active_adapter()
            provider_name = self.config.providers.active

            # Find the actual provider name being used
            for name, adapter in self.adapters.items():
                if adapter is active_adapter:
                    provider_name = name
                    break

            logger.info(
                event="chat_request_start",
                message=f"Processing chat request with {provider_name}",
                request_id=request.request_id,
                input_length=len(text_input),
                provider=provider_name,
            )
        except ValueError as e:
            logger.error(
                event="no_provider_available",
                message="No AI provider available",
                request_id=request.request_id,
                error=str(e),
            )
            yield WebSocketResponse(
                request_id=request.request_id,
                status="error",
                error=str(e),
            )
            return

        try:
            # Get runtime configuration for active provider
            runtime_config = get_active_provider_config()

            system_prompt = runtime_config["system_prompt"]
            temperature = runtime_config["temperature"]
            max_tokens = runtime_config["max_tokens"]
            model_name = runtime_config["model"]

            adapter_request = AdapterRequest(
                messages=[{"role": "user", "content": text_input}],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
            )

            # Stream the response
            async for adapter_response in active_adapter.chat_completion(adapter_request):  # type: ignore
                # Handle content streaming
                if adapter_response.content:
                    yield WebSocketResponse(
                        request_id=request.request_id,
                        status="chunk",
                        chunk=Chunk(
                            type=ChunkType.TEXT,
                            data=adapter_response.content,
                            metadata={
                                "source": provider_name,
                                "model": model_name,
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
                provider=provider_name,
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

    async def _handle_mcp_request(
        self, request: RouterRequest
    ) -> AsyncGenerator[WebSocketResponse, None]:
        """Handle Model Context Protocol requests for self-configuration."""

        logger.info(
            event="mcp_request_start",
            message="Processing MCP request",
            request_id=request.request_id,
            payload_keys=list(request.payload.keys()),
        )

        try:
            # Handle MCP request through the MCP manager
            mcp_response = await self.mcp_manager.handle_mcp_request(request.payload)

            # Send the MCP response as a chunk
            yield WebSocketResponse(
                request_id=request.request_id,
                status="chunk",
                chunk=Chunk(
                    type=ChunkType.METADATA,
                    data=mcp_response.get("result", mcp_response),
                    metadata={
                        "source": "mcp_service",
                        "mcp_status": mcp_response.get("status", "unknown"),
                        "capability_id": mcp_response.get("capability_id"),
                        "mcp_type": mcp_response.get("type"),
                        "mcp_action": mcp_response.get("action"),
                    },
                ),
            )

            # Send completion
            yield WebSocketResponse(request_id=request.request_id, status="complete")

        except Exception as e:
            logger.error(
                event="mcp_request_error",
                message="MCP request processing failed",
                request_id=request.request_id,
                error=str(e),
            )
            yield WebSocketResponse(
                request_id=request.request_id,
                status="error",
                error=f"MCP processing failed: {str(e)}",
            )

    async def shutdown(self) -> None:
        """Gracefully shutdown the router and cleanup resources."""
        logger.info(event="router_shutdown", message="Router shutting down")

        # TODO: Cleanup adapter connections
        pass
