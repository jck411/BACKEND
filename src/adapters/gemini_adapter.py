"""
Google Gemini adapter for chat completions.

Following PROJECT_RULES.md:
- Async I/O for all operations
- Single responsibility: Google Gemini API integration
- Structured logging with elapsed_ms
- Never log secrets or API keys
- Timeout handling with explicit errors
- MCP integration for dynamic configuration
"""

import os
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GenerationConfig = None
    GENAI_AVAILABLE = False

from adapters.base import AdapterRequest, AdapterResponse, BaseAdapter
from adapters.tool_translator import ToolTranslator
from common.logging import TimedLogger, get_logger

if TYPE_CHECKING:
    from mcp.mcp2025_server import MCP2025Server

logger = get_logger(__name__)


class GeminiAdapter(BaseAdapter):
    """Gemini adapter with MCP-based dynamic configuration."""

    def __init__(self, mcp_server: Optional["MCP2025Server"] = None):
        """
        Initialize Gemini adapter with MCP server.

        Args:
            mcp_server: MCP 2025 server for dynamic configuration (required)
        """
        super().__init__(mcp_server)

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

        # Configure Gemini with API key
        try:
            # Try to use configure if available (may not be exported in all versions)
            genai.configure(api_key=api_key)  # type: ignore
        except AttributeError:
            # Fallback if configure is not available
            os.environ["GOOGLE_API_KEY"] = api_key
            logger.info(
                event="gemini_configure_fallback",
                message="Using environment variable fallback for Gemini API key",
            )

        self.provider_name = "gemini"

        logger.info(
            event="gemini_adapter_initialized",
            message="Gemini adapter initialized with MCP server",
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
                event="gemini_config_fetch_failed",
                error=str(e),
            )
            raise RuntimeError(f"Failed to fetch configuration from MCP server: {str(e)}")

    def supports_function_calling(self) -> bool:
        """Gemini supports function calling."""
        return True

    def supports_streaming(self) -> bool:
        """Gemini supports streaming."""
        return True

    def translate_tools(self, mcp_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert MCP tools to Gemini function declarations format."""
        return ToolTranslator.mcp_to_gemini(mcp_tools)

    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""
        # Fetch current configuration from MCP server
        try:
            config = await self._get_config()
        except Exception as e:
            logger.error(
                event="gemini_config_error",
                error=str(e),
            )
            yield AdapterResponse(
                content=None,
                finish_reason="error",
                metadata={"error": f"Configuration error: {str(e)}", "error_type": "config_error"},
            )
            return

        # Extract configuration values
        model_name = config.get("model", "gemini-1.5-flash")
        default_temperature = config.get("temperature", 0.7)
        default_max_tokens = config.get("max_tokens", 4096)
        system_prompt_config = config.get("system_prompt", "You are a helpful AI assistant.")

        with TimedLogger(
            logger,
            "gemini_chat_completion",
            model=model_name,
            message_count=len(request.messages),
        ):
            try:
                # Prepare messages for Gemini format
                chat_history = []
                user_message = ""
                system_message = request.system_prompt or system_prompt_config

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
                        model_name, system_instruction=system_message
                    )
                    chat = model_with_system.start_chat(history=chat_history)

                    # Create generation config for this request
                    generation_config = GenerationConfig(  # type: ignore
                        temperature=request.temperature or default_temperature,
                        max_output_tokens=request.max_tokens or default_max_tokens,
                    )

                    # Send message and stream response
                    response = chat.send_message(
                        user_message, generation_config=generation_config, stream=True
                    )
                else:
                    # Single message, use the model directly
                    model_with_system = genai.GenerativeModel(  # type: ignore
                        model_name, system_instruction=system_message
                    )

                    # Create generation config for this request
                    generation_config = GenerationConfig(  # type: ignore
                        temperature=request.temperature or default_temperature,
                        max_output_tokens=request.max_tokens or default_max_tokens,
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
            # Get current model from configuration
            config = await self._get_config()
            model_name = config.get("model", "gemini-1.5-flash")

            # Make a very simple request to test connectivity
            model = genai.GenerativeModel(model_name)  # type: ignore
            model.generate_content("hi", generation_config=GenerationConfig(max_output_tokens=1))  # type: ignore
            return True
        except Exception as e:
            logger.warning(
                event="gemini_health_check_failed",
                message="Gemini health check failed",
                error=str(e),
            )
            return False
