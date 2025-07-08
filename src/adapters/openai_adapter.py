"""
OpenAI adapter for chat completions and image generation.

Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: OpenAI API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- MCP integration for dynamic configuration
"""

import os
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

import openai
from openai import AsyncOpenAI

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from adapters.tool_translator import ToolTranslator
from common.logging import TimedLogger, get_logger

if TYPE_CHECKING:
    from mcp.mcp2025_server import MCP2025Server

logger = get_logger(__name__)


class OpenAIAdapter(BaseAdapter):
    """OpenAI adapter with MCP-based dynamic configuration."""

    def __init__(self, mcp_server: Optional["MCP2025Server"] = None):
        """
        Initialize OpenAI adapter with MCP server.

        Args:
            mcp_server: MCP 2025 server for dynamic configuration (required)
        """
        super().__init__(mcp_server)

        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = AsyncOpenAI(api_key=api_key)
        self.provider_name = "openai"

        logger.info(
            event="openai_adapter_initialized",
            message="OpenAI adapter initialized with MCP server",
            has_mcp_server=bool(mcp_server),
        )

    async def _get_config(self) -> Dict[str, Any]:
        """
        Get current configuration from MCP server.

        Returns:
            Current provider configuration

        Raises:
            RuntimeError: If MCP server is unavailable
        """
        if not self.mcp_server:
            raise RuntimeError("MCP server not available - cannot fetch configuration")

        try:
            config = await self.mcp_server.get_active_provider_config()

            # Verify this is the correct provider
            if config.get("provider") != self.provider_name:
                raise RuntimeError(
                    f"Configuration mismatch: expected provider '{self.provider_name}', "
                    f"but MCP server returned '{config.get('provider')}'"
                )

            return config

        except Exception as e:
            logger.error(
                event="openai_config_fetch_failed",
                error=str(e),
            )
            raise RuntimeError(f"Failed to fetch configuration from MCP server: {str(e)}")

    def supports_function_calling(self) -> bool:
        """OpenAI supports function calling."""
        return True

    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True

    def translate_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function calling format."""
        return ToolTranslator.mcp_to_openai(mcp_tools)

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""
        # Fetch current configuration from MCP server
        try:
            config = await self._get_config()
        except Exception as e:
            logger.error(
                event="openai_config_error",
                error=str(e),
            )
            yield AdapterResponse(
                content=None,
                finish_reason="error",
                metadata={"error": f"Configuration error: {str(e)}", "error_type": "config_error"},
            )
            return

        # Extract configuration values
        model = config.get("model", "gpt-4o-mini")
        default_temperature = config.get("temperature", 0.7)
        default_max_tokens = config.get("max_tokens")
        system_prompt_config = config.get("system_prompt", "You are a helpful AI assistant.")

        with TimedLogger(
            logger,
            "openai_chat_completion",
            model=model,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages
                messages = []

                # Add system prompt if provided
                system_prompt = request.system_prompt or system_prompt_config
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                # Add conversation messages
                messages.extend(request.messages)

                # Prepare request parameters
                request_params = {
                    "model": model,
                    "messages": messages,
                    "temperature": request.temperature or default_temperature,
                    "stream": True,
                }

                # Add max_tokens if specified
                if request.max_tokens or default_max_tokens:
                    request_params["max_tokens"] = request.max_tokens or default_max_tokens

                # Add tools if provided via MCP
                if request.mcp_tools:
                    openai_tools = self.translate_tools(request.mcp_tools)
                    request_params["tools"] = openai_tools
                    request_params["tool_choice"] = "auto"

                    logger.info(
                        event="openai_tools_configured",
                        message="Configured OpenAI tools from MCP",
                        mcp_tools_count=len(request.mcp_tools),
                        openai_tools_count=len(openai_tools),
                        mcp_tool_names=[t.get("name") for t in request.mcp_tools],
                        openai_tools_names=[
                            t.get("function", {}).get("name") for t in openai_tools
                        ],
                        detailed_mcp_tools=request.mcp_tools,
                        detailed_openai_tools=openai_tools,
                    )
                else:
                    logger.info(
                        event="openai_no_tools",
                        message="No MCP tools provided to OpenAI adapter",
                        request_has_mcp_tools=bool(request.mcp_tools),
                    )

                # Log the complete request being sent to OpenAI
                logger.info(
                    event="openai_request_prepared",
                    message="Prepared request for OpenAI API",
                    model=request_params["model"],
                    temperature=request_params["temperature"],
                    messages_count=len(request_params["messages"]),
                    has_tools=bool(request_params.get("tools")),
                    tools_count=len(request_params.get("tools", [])),
                    tool_choice=request_params.get("tool_choice"),
                    max_tokens=request_params.get("max_tokens"),
                    stream=request_params["stream"],
                    full_request_params=request_params,  # Log full params for debugging
                )

                # Make streaming request
                stream = await self.client.chat.completions.create(**request_params)

                # Process streaming response - IMMEDIATE forwarding, no delays
                chunk_count = 0
                accumulated_tool_calls = {}  # Track tool calls being built
                async for chunk in stream:
                    chunk_count += 1

                    logger.info(
                        event="openai_chunk_received",
                        message="Received chunk from OpenAI",
                        chunk_number=chunk_count,
                        has_choices=bool(chunk.choices),
                        choice_count=len(chunk.choices) if chunk.choices else 0,
                    )

                    if not chunk.choices:
                        logger.warning(
                            event="openai_chunk_no_choices",
                            message="OpenAI chunk has no choices",
                            chunk_number=chunk_count,
                        )
                        continue

                    choice = chunk.choices[0]
                    delta = choice.delta

                    logger.info(
                        event="openai_delta_analysis",
                        message="Analyzing OpenAI delta",
                        chunk_number=chunk_count,
                        has_content=bool(delta.content),
                        content_length=len(delta.content) if delta.content else 0,
                        content_preview=delta.content[:50] if delta.content else None,
                        has_tool_calls=bool(delta.tool_calls),
                        finish_reason=choice.finish_reason,
                    )

                    # IMMEDIATE streaming - forward content chunks instantly
                    if delta.content:
                        adapter_response = AdapterResponse(
                            content=delta.content, metadata={"type": "content_delta"}
                        )

                        logger.info(
                            event="openai_yielding_content",
                            message="Yielding content from OpenAI adapter",
                            chunk_number=chunk_count,
                            content_length=len(delta.content),
                        )

                        yield adapter_response

                    # Handle tool calls - accumulate across chunks
                    if delta.tool_calls:
                        logger.info(
                            event="openai_tool_calls_detected",
                            message="OpenAI tool calls detected in delta",
                            chunk_number=chunk_count,
                            tool_calls_count=len(delta.tool_calls),
                            raw_tool_calls=[
                                {
                                    "id": tc.id,
                                    "type": tc.type if hasattr(tc, "type") else None,
                                    "function_name": tc.function.name if tc.function else None,
                                    "function_args": tc.function.arguments if tc.function else None,
                                }
                                for tc in delta.tool_calls
                            ],
                        )

                        # Accumulate tool call data across chunks
                        for tool_call in delta.tool_calls:
                            if tool_call.function:
                                tool_id = tool_call.id

                                if tool_id not in accumulated_tool_calls:
                                    accumulated_tool_calls[tool_id] = {
                                        "id": tool_id,
                                        "name": tool_call.function.name,
                                        "arguments": "",
                                    }

                                # Accumulate arguments (they come in pieces)
                                if tool_call.function.arguments:
                                    accumulated_tool_calls[tool_id][
                                        "arguments"
                                    ] += tool_call.function.arguments

                                logger.info(
                                    event="openai_tool_call_accumulated",
                                    message="Accumulated tool call data",
                                    tool_call_id=tool_id,
                                    tool_name=tool_call.function.name,
                                    current_args_chunk=tool_call.function.arguments,
                                    total_accumulated_args=accumulated_tool_calls[tool_id][
                                        "arguments"
                                    ],
                                    accumulated_length=len(
                                        accumulated_tool_calls[tool_id]["arguments"]
                                    ),
                                )

                    # Handle completion - send accumulated tool calls if any
                    if choice.finish_reason:
                        logger.info(
                            event="openai_completion",
                            message="OpenAI completion received",
                            chunk_number=chunk_count,
                            finish_reason=choice.finish_reason,
                            total_chunks_processed=chunk_count,
                            accumulated_tool_calls_count=len(accumulated_tool_calls),
                        )

                        # Send completed tool calls if any were accumulated
                        if accumulated_tool_calls:
                            completed_tool_calls = list(accumulated_tool_calls.values())

                            logger.info(
                                event="openai_yielding_completed_tool_calls",
                                message="Yielding completed tool calls from OpenAI adapter",
                                tool_count=len(completed_tool_calls),
                                tool_calls_data=completed_tool_calls,
                            )

                            yield AdapterResponse(
                                content=None,
                                tool_calls=completed_tool_calls,
                                metadata={"type": "tool_calls"},
                            )

                        yield AdapterResponse(
                            content=None,
                            finish_reason=choice.finish_reason,
                            metadata={"type": "completion", "total_chunks": chunk_count},
                        )
                        break

                logger.info(
                    event="openai_stream_complete",
                    message="OpenAI streaming completed",
                    total_chunks=chunk_count,
                )

            except openai.APITimeoutError as e:
                logger.error(
                    event="openai_timeout",
                    message="OpenAI API timeout",
                    error=str(e),
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": "API timeout", "error_type": "timeout"},
                )

            except openai.RateLimitError as e:
                logger.error(
                    event="openai_rate_limit",
                    message="OpenAI rate limit exceeded",
                    error=str(e),
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": "Rate limit exceeded", "error_type": "rate_limit"},
                )

            except openai.APIError as e:
                logger.error(
                    event="openai_api_error",
                    message="OpenAI API error",
                    error=str(e),
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": str(e), "error_type": "api_error"},
                )

    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate an image using DALL-E."""

        with TimedLogger(
            logger,
            "openai_image_generation",
            prompt_length=len(prompt),
        ):
            try:
                response = await self.client.images.generate(
                    model=kwargs.get("model", "dall-e-3"),
                    prompt=prompt,
                    size=kwargs.get("size", "1024x1024"),
                    quality=kwargs.get("quality", "standard"),
                    n=1,
                )

                if response.data and len(response.data) > 0 and response.data[0].url:
                    return response.data[0].url
                else:
                    raise ValueError("No image URL returned from OpenAI")

            except openai.APIError as e:
                logger.error(
                    event="openai_image_error",
                    message="OpenAI image generation error",
                    error=str(e),
                )
                raise

    async def health_check(self) -> bool:
        """Check OpenAI API health by making a minimal request."""
        try:
            # Get current model from configuration
            config = await self._get_config()
            model = config.get("model", "gpt-4o-mini")

            # Make a very simple request to test connectivity
            await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning(
                event="openai_health_check_failed",
                message="OpenAI health check failed",
                error=str(e),
            )
            return False
