"""
OpenRouter adapter for multi-model access.

OpenRouter provides access to 100+ AI models through an OpenAI-compatible API.
Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: OpenRouter API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- Future-ready for MCP tool integration

Note: Configuration is temporary and will move to MCP service later.
"""

import os
from typing import Any, AsyncGenerator, Dict

import openai
from openai import AsyncOpenAI

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from common.logging import TimedLogger, get_logger

logger = get_logger(__name__)


class OpenRouterAdapter(BaseAdapter):
    """OpenRouter adapter for multi-model access."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenRouter adapter."""
        super().__init__(config)

        # Get API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # OpenRouter uses OpenAI-compatible API
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

        self.model = config.get("model", "anthropic/claude-3-sonnet")
        self.default_temperature = config.get("temperature", 0.7)
        self.default_max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")

        logger.info(
            event="openrouter_adapter_initialized",
            message="OpenRouter adapter initialized",
            model=self.model,
            temperature=self.default_temperature,
        )

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""

        with TimedLogger(
            logger,
            "openrouter_chat_completion",
            model=self.model,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages (OpenAI-compatible format)
                messages = []

                # Add system prompt if provided
                system_prompt = request.system_prompt or self.system_prompt
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                # Add conversation messages
                messages.extend(request.messages)

                # Make streaming request (OpenAI-compatible)
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=request.temperature or self.default_temperature,
                    max_tokens=request.max_tokens or self.default_max_tokens,
                    stream=True,
                )

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
                                "model_used": self.model,
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
            # Make a very simple request to test connectivity
            await self.client.chat.completions.create(
                model=self.model,
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
