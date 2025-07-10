"""
Request router for orchestrating adapter communication.

Added 2025-07-05: Core router implementation with simplified OpenAI adapter integration.
Updated 2025-07-06: Multi-provider support with strict mode (no fallbacks).
Updated 2025-07-07: MCP integration for self-configuration capabilities.
Updated 2025-07-08: MCP server as single source of truth for configuration.
Following PROJECT_RULES.md:
- Async I/O for all operations
- Timeout handling with explicit errors
- Structured logging with elapsed_ms
- Single responsibility per class
- MCP integration for dynamic configuration
"""

import asyncio
import os
from typing import AsyncGenerator, Dict, Any, Optional, TYPE_CHECKING

from adapters.base import AdapterRequest, BaseAdapter
from adapters.openai_adapter import OpenAIAdapter
from common.config import Config
from common.logging import TimedLogger, get_logger
from common.models import Chunk, ChunkType, WebSocketResponse
from router.message_types import RequestType, RouterRequest

if TYPE_CHECKING:
    from mcp.mcp2025_server import MCP2025Server

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

    def __init__(self, config: Config, mcp_server: Optional["MCP2025Server"] = None):
        self.config = config
        self.mcp_server = mcp_server
        self.adapters: Dict[str, BaseAdapter] = {}

        # Initialize all available adapters with MCP server
        self._initialize_adapters()

        logger.info(
            event="router_initialized",
            message="Router initialized with MCP server for dynamic configuration",
            timeout=config.router.request_timeout,
            max_retries=config.router.max_retries,
            available_providers=list(self.adapters.keys()),
            active_provider=config.providers.active,
            has_mcp_server=bool(mcp_server),
        )

    def _initialize_adapters(self) -> None:
        """Initialize all available adapters with MCP server."""
        if not self.mcp_server:
            logger.error(
                event="adapter_initialization_error",
                message="Cannot initialize adapters without MCP server",
            )
            raise RuntimeError("MCP server required for adapter initialization")

        try:
            # Initialize OpenAI adapter
            if os.getenv("OPENAI_API_KEY"):
                self.adapters["openai"] = OpenAIAdapter(self.mcp_server)
                logger.info(
                    event="openai_adapter_loaded",
                    message="OpenAI adapter initialized with MCP server",
                )

            # Initialize Anthropic adapter
            if os.getenv("ANTHROPIC_API_KEY") and AnthropicAdapter is not None:
                self.adapters["anthropic"] = AnthropicAdapter(self.mcp_server)
                logger.info(
                    event="anthropic_adapter_loaded",
                    message="Anthropic adapter initialized with MCP server",
                )

            # Initialize Gemini adapter
            if os.getenv("GEMINI_API_KEY") and GeminiAdapter is not None:
                self.adapters["gemini"] = GeminiAdapter(self.mcp_server)
                logger.info(
                    event="gemini_adapter_loaded",
                    message="Gemini adapter initialized with MCP server",
                )

            # Initialize OpenRouter adapter
            if os.getenv("OPENROUTER_API_KEY") and OpenRouterAdapter is not None:
                self.adapters["openrouter"] = OpenRouterAdapter(self.mcp_server)
                logger.info(
                    event="openrouter_adapter_loaded",
                    message="OpenRouter adapter initialized with MCP server",
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

    async def _get_active_adapter(self) -> BaseAdapter:
        """Get the active adapter based on MCP server configuration."""
        if not self.mcp_server:
            raise RuntimeError("MCP server not available - cannot determine active provider")

        # Get active provider from MCP server
        config = await self.mcp_server.get_active_provider_config()
        active_provider = config.get("provider")

        if not active_provider:
            raise RuntimeError("No active provider configured in MCP server")

        # Strict mode: fail fast if provider not available
        if active_provider not in self.adapters:
            raise ValueError(
                f"Active provider '{active_provider}' not available. "
                f"Available providers: {list(self.adapters.keys())}. "
                f"Check your API keys and configuration."
            )

        logger.info(
            event="active_provider_selected",
            message="Active provider selected from MCP server",
            provider=active_provider,
        )

        return self.adapters[active_provider]

    async def get_active_provider_config(self) -> Dict[str, Any]:
        """Get configuration for active provider from MCP server."""
        if not self.mcp_server:
            raise RuntimeError("MCP server not available - cannot fetch configuration")

        try:
            # Get configuration directly from MCP server
            config = await self.mcp_server.get_active_provider_config()
            return config
        except Exception as e:
            logger.error(
                event="mcp_config_error",
                message="Failed to get config from MCP server",
                error=str(e),
            )
            raise RuntimeError(f"Failed to fetch configuration from MCP server: {str(e)}")

    async def get_mcp_tools(self, tool_names: list[str] | None = None) -> list[dict]:
        """
        Get tools from MCP service (canonical source).
        Router delegates tool management to MCP.
        """
        if not self.mcp_server:
            logger.warning(
                event="mcp_tools_no_server",
                message="No MCP server available for tool retrieval",
            )
            return []

        try:
            logger.info(
                event="getting_mcp_tools",
                message="Retrieving MCP tools from MCP server",
                requested_tools=tool_names,
            )

            # Get tools from MCP server's tool registry
            all_tools = await self.mcp_server.tool_registry.list_tools()

            # Convert tools to MCP format (same as _handle_tools_list)
            mcp_tools = []
            for tool in all_tools:
                mcp_tool = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": self._convert_tool_parameters_to_schema(tool),
                }
                mcp_tools.append(mcp_tool)

            # Filter to requested tools if specified
            if tool_names:
                filtered_tools = [tool for tool in mcp_tools if tool["name"] in tool_names]
                logger.info(
                    event="mcp_tools_filtered",
                    message="Returning filtered MCP tools",
                    requested_tools=tool_names,
                    returned_tools=[tool["name"] for tool in filtered_tools],
                )
                return filtered_tools

            logger.info(
                event="mcp_tools_returned",
                message="Returning all available MCP tools",
                tools_count=len(mcp_tools),
                tools=[tool["name"] for tool in mcp_tools],
            )

            return mcp_tools

        except Exception as e:
            logger.error(event="mcp_tools_error", message="Failed to get MCP tools", error=str(e))
            return []

    def _convert_tool_parameters_to_schema(self, tool) -> Dict[str, Any]:
        """Convert tool parameters to JSON Schema format."""
        if not tool.parameters:
            return {"type": "object", "properties": {}, "required": []}

        properties = {}
        required = []

        for param in tool.parameters:
            # Convert parameter to JSON Schema
            prop_schema: Dict[str, Any] = {
                "type": param.type.value,
                "description": param.description,
            }

            if param.enum:
                prop_schema["enum"] = param.enum
            if param.minimum is not None:
                prop_schema["minimum"] = param.minimum
            if param.maximum is not None:
                prop_schema["maximum"] = param.maximum
            if param.pattern:
                prop_schema["pattern"] = param.pattern
            if param.default is not None:
                prop_schema["default"] = param.default

            # Handle array items
            if param.type.value == "array" and param.items:
                prop_schema["items"] = {
                    "type": param.items.type.value,
                    "description": param.items.description,
                }
                # Add enum if the items have it
                if param.items.enum:
                    prop_schema["items"]["enum"] = param.items.enum

            properties[param.name] = prop_schema

            if param.required:
                required.append(param.name)

        return {"type": "object", "properties": properties, "required": required}

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
            # Get active adapter
            active_adapter = await self._get_active_adapter()

            # Get configuration from MCP service
            mcp_config = await self.get_active_provider_config()
            provider_name = mcp_config.get("provider", self.config.providers.active)

            system_prompt = mcp_config.get("system_prompt", "You are a helpful AI assistant.")
            temperature = mcp_config.get("temperature", 0.7)
            max_tokens = mcp_config.get("max_tokens", 2048)
            model_name = mcp_config.get("model", "gpt-4o-mini")

            # Get MCP tools from registry (canonical source)
            mcp_tools = await self.get_mcp_tools()

            logger.info(
                event="mcp_tools_retrieved",
                message="Retrieved MCP tools for chat request",
                request_id=request.request_id,
                mcp_tools_available=bool(mcp_tools),
                mcp_tools_count=len(mcp_tools) if mcp_tools else 0,
                mcp_tool_names=[tool.get("name") for tool in mcp_tools] if mcp_tools else [],
                detailed_tools=mcp_tools,  # Log full tool definitions
            )

            adapter_request = AdapterRequest(
                messages=[{"role": "user", "content": text_input}],
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                mcp_tools=mcp_tools if mcp_tools else None,
            )

            logger.info(
                event="adapter_request_created",
                message="Created adapter request with MCP tools",
                request_id=request.request_id,
                adapter_request_has_tools=bool(adapter_request.mcp_tools),
                adapter_request_tool_count=(
                    len(adapter_request.mcp_tools) if adapter_request.mcp_tools else 0
                ),
                messages_count=len(adapter_request.messages),
                temperature=adapter_request.temperature,
                max_tokens=adapter_request.max_tokens,
            )

            logger.info(
                event="chat_request_start",
                message=f"Processing chat request with {provider_name}",
                request_id=request.request_id,
                input_length=len(text_input),
                provider=provider_name,
                has_tools=bool(mcp_tools),
                tool_count=len(mcp_tools) if mcp_tools else 0,
            )
        except Exception as e:
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
            async for adapter_response in active_adapter.chat_completion(adapter_request):  # type: ignore
                # Log every adapter response for debugging
                logger.info(
                    event="adapter_response_received",
                    message="Received response from adapter",
                    request_id=request.request_id,
                    has_content=bool(adapter_response.content),
                    content_length=len(adapter_response.content) if adapter_response.content else 0,
                    has_tool_calls=bool(adapter_response.tool_calls),
                    has_finish_reason=bool(adapter_response.finish_reason),
                    metadata=adapter_response.metadata,
                )

                # Handle content streaming
                if adapter_response.content:
                    websocket_response = WebSocketResponse(
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

                    logger.info(
                        event="websocket_response_yielding",
                        message="Yielding content chunk to WebSocket",
                        request_id=request.request_id,
                        chunk_length=len(adapter_response.content),
                        chunk_preview=(
                            adapter_response.content[:50] + "..."
                            if len(adapter_response.content) > 50
                            else adapter_response.content
                        ),
                    )

                    yield websocket_response

                # Handle tool calls - EXECUTE LOCALLY VIA MCP 2025, DON'T SEND TO FRONTEND
                if adapter_response.tool_calls:
                    logger.info(
                        event="tool_calls_received_for_mcp_execution",
                        message="Executing tool calls locally via MCP 2025 protocol",
                        request_id=request.request_id,
                        tool_count=len(adapter_response.tool_calls),
                        tool_names=[tc.name for tc in adapter_response.tool_calls],
                    )

                    # Execute each tool call through MCP 2025 server
                    tool_results = []
                    for tool_call in adapter_response.tool_calls:
                        tool_name = tool_call.name
                        tool_arguments = tool_call.arguments
                        tool_id = tool_call.id

                        logger.info(
                            event="executing_tool_via_mcp2025",
                            message="Executing tool call via MCP 2025 protocol",
                            request_id=request.request_id,
                            tool_name=tool_name,
                            tool_id=tool_id,
                        )

                        try:
                            # Execute through MCP 2025 server for full compliance
                            from mcp.mcp2025_server import get_mcp2025_server
                            from mcp.jsonrpc import JSONRPCHandler, MCPMethods, MCPToolsCallParams

                            mcp_server = get_mcp2025_server()

                            # Parse JSON arguments if they come as string
                            if isinstance(tool_arguments, str):
                                import json

                                try:
                                    tool_arguments = json.loads(tool_arguments)
                                except json.JSONDecodeError:
                                    tool_arguments = {"request": tool_arguments}

                            # Create MCP 2025 compliant tool call request
                            mcp_request = JSONRPCHandler.create_request(
                                id=f"mcp-{tool_id}",
                                method=MCPMethods.TOOLS_CALL,
                                params=MCPToolsCallParams(
                                    name=tool_name, arguments=tool_arguments
                                ).model_dump(),
                            )

                            # Execute through MCP 2025 server
                            mcp_response = await mcp_server._handle_request(mcp_request)

                            # Type-safe response handling
                            from mcp.jsonrpc import JSONRPCResponse, JSONRPCErrorResponse

                            if isinstance(mcp_response, JSONRPCResponse):
                                # Success - extract content from MCP response
                                result_data = mcp_response.result
                                result_content = (
                                    result_data.get("content", [])
                                    if isinstance(result_data, dict)
                                    else []
                                )
                                result_text = []

                                # Extract text from multi-type content
                                for content_item in result_content:
                                    if (
                                        isinstance(content_item, dict)
                                        and content_item.get("type") == "text"
                                    ):
                                        result_text.append(content_item.get("text", ""))

                                success_message = (
                                    "\n".join(result_text) or "Tool executed successfully"
                                )

                                logger.info(
                                    event="mcp_tool_execution_success",
                                    message="Tool executed successfully via MCP 2025",
                                    request_id=request.request_id,
                                    tool_name=tool_name,
                                    content_types=[
                                        c.get("type") for c in result_content if isinstance(c, dict)
                                    ],
                                )

                                tool_results.append(
                                    {
                                        "tool_call_id": tool_id,
                                        "result": success_message,
                                        "success": True,
                                        "mcp_content": result_content,  # Full MCP content for debugging
                                    }
                                )

                            elif isinstance(mcp_response, JSONRPCErrorResponse):
                                # Error - extract error message
                                error_message = (
                                    mcp_response.error.message
                                    if mcp_response.error
                                    else "Tool execution failed"
                                )

                                logger.error(
                                    event="mcp_tool_execution_failed",
                                    message="Tool execution failed via MCP 2025",
                                    request_id=request.request_id,
                                    tool_name=tool_name,
                                    error=error_message,
                                )

                                tool_results.append(
                                    {
                                        "tool_call_id": tool_id,
                                        "result": f"Tool execution failed: {error_message}",
                                        "success": False,
                                    }
                                )

                            else:
                                # Unexpected response type
                                logger.error(
                                    event="mcp_unexpected_response",
                                    message="Unexpected MCP response type",
                                    request_id=request.request_id,
                                    tool_name=tool_name,
                                    response_type=type(mcp_response).__name__,
                                )

                                tool_results.append(
                                    {
                                        "tool_call_id": tool_id,
                                        "result": "Tool execution failed: Unexpected response format",
                                        "success": False,
                                    }
                                )

                        except Exception as e:
                            logger.error(
                                event="mcp_tool_execution_exception",
                                message="Exception during MCP 2025 tool execution",
                                request_id=request.request_id,
                                tool_name=tool_name,
                                error=str(e),
                            )

                            tool_results.append(
                                {
                                    "tool_call_id": tool_id,
                                    "result": f"Tool execution error: {str(e)}",
                                    "success": False,
                                }
                            )

                    # Continue conversation with LLM following MCP best practices
                    # Construct proper tool result messages for LLM continuation
                    tool_result_messages = []
                    for result in tool_results:
                        tool_result_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": result["tool_call_id"],
                                "content": result["result"],
                            }
                        )

                    # Build complete conversation history with tool results
                    complete_messages = adapter_request.messages.copy()

                    # Add assistant message with tool calls
                    assistant_message: Dict[str, Any] = {"role": "assistant", "content": ""}
                    if adapter_response.content:
                        assistant_message["content"] = adapter_response.content

                    # Format tool calls for OpenAI API requirements
                    if adapter_response.tool_calls:
                        formatted_tool_calls = []
                        for tool_call in adapter_response.tool_calls:
                            formatted_tool_call = {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.name,
                                    "arguments": tool_call.arguments,
                                },
                            }
                            formatted_tool_calls.append(formatted_tool_call)
                        assistant_message["tool_calls"] = formatted_tool_calls

                    complete_messages.append(assistant_message)

                    # Add tool result messages
                    complete_messages.extend(tool_result_messages)

                    # Create follow-up request for LLM to process tool results
                    follow_up_request = AdapterRequest(
                        messages=complete_messages,
                        temperature=adapter_request.temperature,
                        max_tokens=adapter_request.max_tokens,
                        system_prompt=adapter_request.system_prompt,
                        mcp_tools=None,  # Disable tools for follow-up to prevent infinite loops
                    )

                    logger.info(
                        event="continuing_conversation_with_mcp_results",
                        message="Continuing conversation with LLM after MCP tool execution",
                        request_id=request.request_id,
                        tool_results_count=len(tool_results),
                        successful_tools=sum(1 for r in tool_results if r["success"]),
                    )

                    # Continue conversation with LLM to get explanation/summary
                    try:
                        async for follow_up_response in active_adapter.chat_completion(
                            follow_up_request
                        ):  # type: ignore
                            # Log follow-up response
                            logger.info(
                                event="mcp_follow_up_response_received",
                                message="Received follow-up response after MCP tool execution",
                                request_id=request.request_id,
                                has_content=bool(follow_up_response.content),
                                content_length=(
                                    len(follow_up_response.content)
                                    if follow_up_response.content
                                    else 0
                                ),
                            )

                            # Forward follow-up content to frontend
                            if follow_up_response.content:
                                websocket_response = WebSocketResponse(
                                    request_id=request.request_id,
                                    status="chunk",
                                    chunk=Chunk(
                                        type=ChunkType.TEXT,
                                        data=follow_up_response.content,
                                        metadata={
                                            "source": provider_name,
                                            "model": model_name,
                                            "type": "mcp_tool_execution_explanation",
                                            "mcp_compliant": True,
                                        },
                                    ),
                                )

                                logger.info(
                                    event="mcp_follow_up_content_yielding",
                                    message="Yielding MCP-compliant follow-up content to WebSocket",
                                    request_id=request.request_id,
                                    chunk_length=len(follow_up_response.content),
                                )

                                yield websocket_response

                            # Handle follow-up completion
                            if follow_up_response.finish_reason:
                                logger.info(
                                    event="mcp_follow_up_completion",
                                    message="MCP-compliant follow-up conversation completed",
                                    request_id=request.request_id,
                                    finish_reason=follow_up_response.finish_reason,
                                )
                                break

                    except Exception as e:
                        logger.error(
                            event="mcp_follow_up_error",
                            message="Error in MCP follow-up conversation",
                            request_id=request.request_id,
                            error=str(e),
                        )

                        # Send error response to frontend
                        yield WebSocketResponse(
                            request_id=request.request_id,
                            status="error",
                            error=f"MCP follow-up conversation failed: {str(e)}",
                        )
                        return

                    # MCP tool execution and explanation complete
                    logger.info(
                        event="mcp_tool_flow_completed",
                        message="Complete MCP tool execution flow finished",
                        request_id=request.request_id,
                        tools_executed=len(tool_results),
                    )

                    # Return here as we've completed the full MCP flow
                    return

                # Handle completion
                if adapter_response.finish_reason:
                    logger.info(
                        event="completion_received",
                        message="Received completion from adapter",
                        request_id=request.request_id,
                        finish_reason=adapter_response.finish_reason,
                    )

                    # Send completion
                    completion_response = WebSocketResponse(
                        request_id=request.request_id, status="complete"
                    )

                    logger.info(
                        event="completion_websocket_response",
                        message="Yielding completion to WebSocket",
                        request_id=request.request_id,
                    )

                    yield completion_response
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
        """Handle Model Context Protocol requests - delegate to MCP service."""

        logger.info(
            event="mcp_request_start",
            message="Processing MCP request - delegating to MCP service",
            request_id=request.request_id,
            payload_keys=list(request.payload.keys()),
        )

        try:
            # Self-configuration service removed in simplified approach
            # LLM now handles configuration directly through MCP tools

            # Return a simple message explaining the new approach
            result = {
                "message": "Configuration is now handled directly by the LLM using MCP tools. Simply ask me to adjust my settings in natural language.",
                "status": "info",
                "mcp_tools_available": [
                    "ai_configure",
                    "show_current_config",
                    "list_available_models",
                    "switch_provider",
                    "reset_config",
                ],
            }

            # Send the MCP response as a chunk
            yield WebSocketResponse(
                request_id=request.request_id,
                status="chunk",
                chunk=Chunk(
                    type=ChunkType.METADATA,
                    data=result.get("message", result),
                    metadata={
                        "source": "mcp_service",
                        "mcp_status": result.get("status", "unknown"),
                        "confidence": result.get("confidence"),
                        "mcp_type": "configuration",
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
