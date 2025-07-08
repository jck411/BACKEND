"""
Anthropic adapter for Claude chat completions.

Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: Anthropic API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- MCP integration for dynamic configuration
"""

import os
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    anthropic = None
    AsyncAnthropic = None

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from adapters.tool_translator import ToolTranslator
from common.logging import TimedLogger, get_logger

if TYPE_CHECKING:
    from mcp.mcp2025_server import MCP2025Server

logger = get_logger(__name__)


class AnthropicAdapter(BaseAdapter):
    """Anthropic adapter with MCP-based dynamic configuration."""

    def __init__(self, mcp_server: Optional["MCP2025Server"] = None):
        """
        Initialize Anthropic adapter with MCP server.

        Args:
            mcp_server: MCP 2025 server for dynamic configuration (required)
        """
        super().__init__(mcp_server)

        if anthropic is None:
            raise ImportError("anthropic package not installed. Install with: uv add anthropic")

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        if AsyncAnthropic is None:
            raise ImportError("anthropic package not properly imported")

        self.client = AsyncAnthropic(api_key=api_key)
        self.provider_name = "anthropic"

        logger.info(
            event="anthropic_adapter_initialized",
            message="Anthropic adapter initialized with MCP server",
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
                event="anthropic_config_fetch_failed",
                error=str(e),
            )
            raise RuntimeError(f"Failed to fetch configuration from MCP server: {str(e)}")

    def supports_function_calling(self) -> bool:
        """Anthropic supports function calling."""
        return True

    def supports_streaming(self) -> bool:
        """Anthropic supports streaming."""
        return True

    def translate_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Anthropic tools format."""
        return ToolTranslator.mcp_to_anthropic(mcp_tools)

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""
        # Fetch current configuration from MCP server
        try:
            config = await self._get_config()
        except Exception as e:
            logger.error(
                event="anthropic_config_error",
                error=str(e),
            )
            yield AdapterResponse(
                content=None,
                finish_reason="error",
                metadata={"error": f"Configuration error: {str(e)}", "error_type": "config_error"},
            )
            return

        # Extract configuration values
        model = config.get("model", "claude-3-5-sonnet-20241022")
        default_temperature = config.get("temperature", 0.7)
        default_max_tokens = config.get("max_tokens", 4096)
        system_prompt_config = config.get("system_prompt", "You are a helpful AI assistant.")

        with TimedLogger(
            logger,
            "anthropic_chat_completion",
            model=model,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages for Anthropic format
                messages = []
                system_message = request.system_prompt or system_prompt_config

                # Convert OpenAI format to Anthropic format
                for msg in request.messages:
                    if msg["role"] == "system":
                        # System messages are handled separately in Anthropic
                        system_message = msg["content"]
                    else:
                        messages.append({"role": msg["role"], "content": msg["content"]})

                # Prepare request parameters
                request_params = {
                    "model": model,
                    "messages": messages,
                    "system": system_message,
                    "temperature": request.temperature or default_temperature,
                    "max_tokens": request.max_tokens or default_max_tokens,
                }

                # Add tools if provided via MCP
                if request.mcp_tools:
                    anthropic_tools = self.translate_tools(request.mcp_tools)
                    request_params["tools"] = anthropic_tools

                # Make streaming request
                async with self.client.messages.stream(**request_params) as stream:
                    # Process streaming response - IMMEDIATE forwarding, no delays
                    async for event in stream:
                        if event.type == "content_block_delta":
                            # IMMEDIATE streaming - forward content chunks instantly
                            text_content = getattr(event.delta, "text", None)
                            if text_content:
                                yield AdapterResponse(
                                    content=text_content, metadata={"type": "content_delta"}
                                )

                        elif event.type == "content_block_start":
                            # Handle tool use blocks
                            if (
                                hasattr(event.content_block, "type")
                                and event.content_block.type == "tool_use"
                            ):
                                tool_call = {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "arguments": event.content_block.input,
                                }
                                yield AdapterResponse(
                                    content=None,
                                    tool_calls=[tool_call],
                                    metadata={"type": "tool_calls"},
                                )

                        elif event.type == "message_stop":
                            # Handle completion - NO content, only completion signal
                            final_message = await stream.get_final_message()
                            usage = final_message.usage if hasattr(final_message, "usage") else None

                            yield AdapterResponse(
                                content=None,  # Never send content here - prevents duplication
                                finish_reason="stop",
                                metadata={
                                    "total_tokens": (
                                        usage.output_tokens + usage.input_tokens if usage else None
                                    ),
                                    "input_tokens": usage.input_tokens if usage else None,
                                    "output_tokens": usage.output_tokens if usage else None,
                                },
                            )
                            break

            except Exception as e:
                # Handle various Anthropic API exceptions
                error_type = "api_error"
                error_message = str(e)

                # Check for specific error types by string matching
                if "timeout" in error_message.lower():
                    error_type = "timeout"
                    logger.error(
                        event="anthropic_timeout",
                        message="Anthropic API timeout",
                        error=error_message,
                    )
                elif "rate limit" in error_message.lower() or "quota" in error_message.lower():
                    error_type = "rate_limit"
                    logger.error(
                        event="anthropic_rate_limit",
                        message="Anthropic rate limit exceeded",
                        error=error_message,
                    )
                else:
                    logger.error(
                        event="anthropic_api_error",
                        message="Anthropic API error",
                        error=error_message,
                    )

                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": error_message, "error_type": error_type},
                )

    async def health_check(self) -> bool:
        """Check Anthropic API health by making a minimal request."""
        try:
            # Get current model from configuration
            config = await self._get_config()
            model = config.get("model", "claude-3-5-sonnet-20241022")

            # Make a very simple request to test connectivity
            await self.client.messages.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning(
                event="anthropic_health_check_failed",
                message="Anthropic health check failed",
                error=str(e),
            )
            return False
