"""
Anthropic adapter for Claude chat completions.

Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: Anthropic API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- Future-ready for MCP tool integration

Note: Configuration is temporary and will move to MCP service later.
"""

import os
from typing import Any, AsyncGenerator, Dict

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    anthropic = None
    AsyncAnthropic = None

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from common.logging import TimedLogger, get_logger

logger = get_logger(__name__)


class AnthropicAdapter(BaseAdapter):
    """Anthropic Claude adapter for chat completions."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic adapter."""
        super().__init__(config)

        if anthropic is None:
            raise ImportError("anthropic package not installed. Install with: uv add anthropic")

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        if AsyncAnthropic is None:
            raise ImportError("anthropic package not properly imported")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.default_temperature = config.get("temperature", 0.7)
        self.default_max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")

        logger.info(
            event="anthropic_adapter_initialized",
            message="Anthropic adapter initialized",
            model=self.model,
            temperature=self.default_temperature,
        )

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""

        with TimedLogger(
            logger,
            "anthropic_chat_completion",
            model=self.model,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages for Anthropic format
                messages = []
                system_message = request.system_prompt or self.system_prompt

                # Convert OpenAI format to Anthropic format
                for msg in request.messages:
                    if msg["role"] == "system":
                        # System messages are handled separately in Anthropic
                        system_message = msg["content"]
                    else:
                        messages.append({"role": msg["role"], "content": msg["content"]})

                # Make streaming request
                async with self.client.messages.stream(
                    model=self.model,
                    messages=messages,
                    system=system_message,
                    temperature=request.temperature or self.default_temperature,
                    max_tokens=request.max_tokens or self.default_max_tokens,
                ) as stream:
                    # Process streaming response - IMMEDIATE forwarding, no delays
                    async for event in stream:
                        if event.type == "content_block_delta":
                            # IMMEDIATE streaming - forward content chunks instantly
                            text_content = getattr(event.delta, "text", None)
                            if text_content:
                                yield AdapterResponse(
                                    content=text_content, metadata={"type": "content_delta"}
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
            # Make a very simple request to test connectivity
            await self.client.messages.create(
                model=self.model,
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
