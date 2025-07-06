"""
OpenAI adapter for chat completions and image generation.

Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: OpenAI API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- Future-ready for MCP tool integration
"""

import os
from typing import Any, AsyncGenerator, Dict

import openai
from openai import AsyncOpenAI

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from common.logging import TimedLogger, get_logger

logger = get_logger(__name__)


class OpenAIAdapter(BaseAdapter):
    """OpenAI adapter for simple chat completions."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI adapter."""
        super().__init__(config)

        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = config.get("model", "gpt-4o-mini")
        self.default_temperature = config.get("temperature", 0.7)
        self.default_max_tokens = config.get("max_tokens")
        self.system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")

        logger.info(
            event="openai_adapter_initialized",
            message="OpenAI adapter initialized",
            model=self.model,
            temperature=self.default_temperature,
        )

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""

        with TimedLogger(
            logger,
            "openai_chat_completion",
            model=self.model,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages
                messages = []

                # Add system prompt if provided
                system_prompt = request.system_prompt or self.system_prompt
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                # Add conversation messages
                messages.extend(request.messages)

                # Make streaming request (no tools for now - will be handled by MCP later)
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
                                )
                            },
                        )
                        break

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
            # Make a very simple request to test connectivity
            await self.client.chat.completions.create(
                model=self.model,
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
