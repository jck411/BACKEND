"""
Google Gemini adapter for chat completions.

Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: Google Gemini API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- Future-ready for MCP tool integration

Note: Configuration is temporary and will move to MCP service later.
"""

import os
from typing import Any, AsyncGenerator, Dict

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GenerationConfig = None
    GENAI_AVAILABLE = False

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from common.logging import TimedLogger, get_logger

logger = get_logger(__name__)


class GeminiAdapter(BaseAdapter):
    """Google Gemini adapter for chat completions."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini adapter."""
        super().__init__(config)

        if genai is None:
            raise ImportError(
                "google-generativeai package not installed. Install with: uv add google-generativeai"
            )

        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        if genai is None or not GENAI_AVAILABLE:
            raise ImportError("google-generativeai package not properly imported")

        genai.configure(api_key=api_key)

        self.model_name = config.get("model", "gemini-1.5-flash")
        self.default_temperature = config.get("temperature", 0.7)
        self.default_max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")

        # Initialize the model
        assert genai is not None  # Type guard for Pylance
        assert GenerationConfig is not None  # Type guard for Pylance

        self.model = genai.GenerativeModel(self.model_name)  # type: ignore

        # Generation configuration
        self.generation_config = GenerationConfig(  # type: ignore
            temperature=self.default_temperature,
            max_output_tokens=self.default_max_tokens,
        )

        logger.info(
            event="gemini_adapter_initialized",
            message="Gemini adapter initialized",
            model=self.model_name,
            temperature=self.default_temperature,
        )

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""

        with TimedLogger(
            logger,
            "gemini_chat_completion",
            model=self.model_name,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages for Gemini format
                chat_history = []
                user_message = ""
                system_message = request.system_prompt or self.system_prompt

                # Convert OpenAI format to Gemini format
                for msg in request.messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    elif msg["role"] == "user":
                        user_message = msg["content"]
                    elif msg["role"] == "assistant":
                        chat_history.append(
                            {
                                "role": "model",  # Gemini uses "model" instead of "assistant"
                                "parts": [msg["content"]],
                            }
                        )

                # If we have chat history, start a chat session
                if chat_history:
                    # Add system instruction to the model
                    model_with_system = genai.GenerativeModel(  # type: ignore
                        self.model_name, system_instruction=system_message
                    )
                    chat = model_with_system.start_chat(history=chat_history)

                    # Create generation config for this request
                    generation_config = GenerationConfig(  # type: ignore
                        temperature=request.temperature or self.default_temperature,
                        max_output_tokens=request.max_tokens or self.default_max_tokens,
                    )

                    # Send message and stream response
                    response = chat.send_message(
                        user_message, generation_config=generation_config, stream=True
                    )
                else:
                    # Single message, use the model directly
                    model_with_system = genai.GenerativeModel(  # type: ignore
                        self.model_name, system_instruction=system_message
                    )

                    # Create generation config for this request
                    generation_config = GenerationConfig(  # type: ignore
                        temperature=request.temperature or self.default_temperature,
                        max_output_tokens=request.max_tokens or self.default_max_tokens,
                    )

                    response = model_with_system.generate_content(
                        user_message, generation_config=generation_config, stream=True
                    )

                # Process streaming response - IMMEDIATE forwarding, no delays
                for chunk in response:
                    if chunk.text:
                        # IMMEDIATE streaming - forward content chunks instantly
                        yield AdapterResponse(
                            content=chunk.text, metadata={"type": "content_delta"}
                        )

                # Handle completion - NO content, only completion signal
                # Note: Gemini doesn't provide explicit finish reasons in streaming
                yield AdapterResponse(
                    content=None,  # Never send content here - prevents duplication
                    finish_reason="stop",
                    metadata={
                        "total_tokens": None,  # Gemini doesn't provide token counts in streaming
                        "prompt_feedback": getattr(response, "prompt_feedback", None),
                    },
                )

            except Exception as e:
                # Handle various Gemini API exceptions
                error_type = "api_error"
                if "quota" in str(e).lower() or "rate limit" in str(e).lower():
                    error_type = "rate_limit"
                elif "timeout" in str(e).lower():
                    error_type = "timeout"

                logger.error(
                    event="gemini_api_error",
                    message="Gemini API error",
                    error=str(e),
                    error_type=error_type,
                )
                yield AdapterResponse(
                    content=None,
                    finish_reason="error",
                    metadata={"error": str(e), "error_type": error_type},
                )

    async def health_check(self) -> bool:
        """Check Gemini API health by making a minimal request."""
        try:
            # Make a very simple request to test connectivity
            model = genai.GenerativeModel(self.model_name)  # type: ignore
            model.generate_content("hi", generation_config=GenerationConfig(max_output_tokens=1))  # type: ignore
            return True
        except Exception as e:
            logger.warning(
                event="gemini_health_check_failed",
                message="Gemini health check failed",
                error=str(e),
            )
            return False
