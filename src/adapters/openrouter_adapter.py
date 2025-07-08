"""
OpenRouter adapter for multi-model access.

OpenRouter provides access to 100+ AI models through an OpenAI-compatible API.
Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: OpenRouter API integration
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


class OpenRouterAdapter(BaseAdapter):
    """OpenRouter adapter with MCP-based dynamic configuration."""

    def __init__(self, mcp_server: Optional["MCP2025Server"] = None):
        """
        Initialize OpenRouter adapter with MCP server.

        Args:
            mcp_server: MCP 2025 server for dynamic configuration (required)
        """
        super().__init__(mcp_server)

        # Get API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # OpenRouter uses OpenAI-compatible API
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.provider_name = "openrouter"

        logger.info(
            event="openrouter_adapter_initialized",
            message="OpenRouter adapter initialized with MCP server",
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
                event="openrouter_config_fetch_failed",
                error=str(e),
            )
            raise RuntimeError(f"Failed to fetch configuration from MCP server: {str(e)}")

    def supports_function_calling(self) -> bool:
        """OpenRouter supports function calling (OpenAI-compatible)."""
        return True

    def supports_streaming(self) -> bool:
        """OpenRouter supports streaming."""
        return True

    def translate_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenRouter (OpenAI-compatible) format."""
        return ToolTranslator.mcp_to_openrouter(mcp_tools)

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""
        # Fetch current configuration from MCP server
        try:
            config = await self._get_config()
        except Exception as e:
            logger.error(
                event="openrouter_config_error",
                error=str(e),
            )
            yield AdapterResponse(
                content=None,
                finish_reason="error",
                metadata={"error": f"Configuration error: {str(e)}", "error_type": "config_error"},
            )
            return

        # Extract configuration values
        model = config.get("model", "anthropic/claude-3-sonnet")
        default_temperature = config.get("temperature", 0.7)
        default_max_tokens = config.get("max_tokens", 4096)
        system_prompt_config = config.get("system_prompt", "You are a helpful AI assistant.")

        with TimedLogger(
            logger,
            "openrouter_chat_completion",
            model=model,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages (OpenAI-compatible format)
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
                    openrouter_tools = self.translate_tools(request.mcp_tools)
                    request_params["tools"] = openrouter_tools
                    request_params["tool_choice"] = "auto"

                # Make streaming request (OpenAI-compatible)
                stream = await self.client.chat.completions.create(**request_params)

                # Process streaming response - IMMEDIATE forwarding, no delays
                async for chunk in stream:
                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    delta = choice.delta

                    # IMMEDIATE streaming - forward content chunks instantly
                    if delta.content:
                        yield AdapterResponse(
                            content=delta.content, metadata={"type": "content_delta"}
                        )

                    # Handle tool calls
                    if delta.tool_calls:
                        tool_calls = []
                        for tool_call in delta.tool_calls:
                            if tool_call.function:
                                tool_calls.append(
                                    {
                                        "id": tool_call.id,
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments,
                                    }
                                )

                        if tool_calls:
                            yield AdapterResponse(
                                content=None, tool_calls=tool_calls, metadata={"type": "tool_calls"}
                            )

                    # Handle completion - NO content, only completion signal
                    if choice.finish_reason:
                        yield AdapterResponse(
                            content=None,  # Never send content here - prevents duplication
                            finish_reason=choice.finish_reason,
                            metadata={
                                "total_tokens": (
                                    getattr(chunk.usage, "total_tokens", None)
                                    if hasattr(chunk, "usage")
                                    else None
                                ),
                                "model_used": model,
                            },
                        )
                        break

            except openai.APITimeoutError as e:
                logger.error(
                    event="openrouter_timeout",
                    message="OpenRouter API timeout",
                    error=str(e),
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": "API timeout", "error_type": "timeout"},
                )

            except openai.RateLimitError as e:
                logger.error(
                    event="openrouter_rate_limit",
                    message="OpenRouter rate limit exceeded",
                    error=str(e),
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": "Rate limit exceeded", "error_type": "rate_limit"},
                )

            except openai.APIError as e:
                logger.error(
                    event="openrouter_api_error",
                    message="OpenRouter API error",
                    error=str(e),
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": str(e), "error_type": "api_error"},
                )

    async def health_check(self) -> bool:
        """Check OpenRouter API health by making a minimal request."""
        try:
            # Get current model from configuration
            config = await self._get_config()
            model = config.get("model", "anthropic/claude-3-sonnet")

            # Make a very simple request to test connectivity
            await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning(
                event="openrouter_health_check_failed",
                message="OpenRouter health check failed",
                error=str(e),
            )
            return False
