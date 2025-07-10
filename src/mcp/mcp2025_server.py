"""
MCP 2025 Compliant Server Implementation

This module implements a fully MCP 2025 compliant server with:
- JSON-RPC 2.0 protocol wrapper
- Initialize/capabilities handshake
- Cursor-based pagination
- Tool list change notifications
- Multi-type tool results

This replaces the legacy HTTP endpoints with proper MCP compliance.
"""

import asyncio
from typing import Dict, Any, Optional, Set
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from datetime import datetime

from common.logging import (
    get_logger,
    should_log_adapter_details,
    log_startup_message,
    log_tool_call_json,
)
from common.runtime_config import get_runtime_config_persistence
from common.config import load_config
from .parameter_schemas import ModelParameterSchemas, PopularModels
from .tool_registry import ToolRegistry, Tool
from .jsonrpc import (
    JSONRPCHandler,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCErrorResponse,
    JSONRPCNotification,
    MCPMethods,
    MCPCapabilities,
    MCPImplementation,
    MCPInitializeParams,
    MCPInitializeResult,
    MCPToolsListParams,
    MCPToolsListResult,
    MCPToolsCallParams,
    MCPToolsCallResult,
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    MCP_TOOL_EXECUTION_ERROR,
)

logger = get_logger(__name__)

# MCP Protocol version
MCP_PROTOCOL_VERSION = "2025-06-18"

# Pagination constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


# Multi-type content support
class ContentType:
    """Standard MCP content types."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    RESOURCE = "resource"
    RESOURCE_LINK = "resource_link"


class MCPServerState:
    """State management for MCP server."""

    def __init__(self):
        self.initialized_clients: Set[str] = set()
        self.notification_subscribers: Set[WebSocket] = set()
        self.tools_version = 0  # Incremented when tools change


class MCP2025Server:
    """
    MCP 2025 Compliant Server.

    Implements full MCP specification including JSON-RPC 2.0 wrapper,
    capabilities negotiation, pagination, and change notifications.
    """

    def __init__(self):
        """Initialize the MCP 2025 server."""
        self.config_persistence = get_runtime_config_persistence()
        self.config_cache = None  # Cache loaded configuration

        # Load main config for MCP settings
        main_config = load_config()
        self.tool_registry = ToolRegistry(mcp_config=main_config.mcp)
        self.state = MCPServerState()

        # Initialize router with both HTTP and WebSocket endpoints
        self.router = APIRouter(prefix="/mcp", tags=["MCP 2025"])
        self._setup_routes()

        # Server capabilities
        self.capabilities = MCPCapabilities(
            tools={"listChanged": True},  # We support tool list change notifications
            logging={},  # Basic logging support
        )

        self.server_info = MCPImplementation(name="MCP Backend Server", version="2025.06.18")

        # Register all configuration tools
        self._register_configuration_tools()

        log_startup_message(
            "MCP 2025 Server Initialized",
            protocol_version=MCP_PROTOCOL_VERSION,
            capabilities=self.capabilities.model_dump(),
        )

    def _setup_routes(self) -> None:
        """Setup MCP 2025 compliant routes."""

        @self.router.post("/jsonrpc")
        async def handle_jsonrpc(request: Request) -> JSONResponse:
            """
            Main JSON-RPC endpoint for MCP protocol.

            Handles both single requests and batch requests according to
            JSON-RPC 2.0 specification.
            """
            try:
                body = await request.json()

                if JSONRPCHandler.is_batch(body):
                    # Handle batch request
                    batch = JSONRPCHandler.validate_batch(body)
                    responses = []

                    for message in batch:
                        if isinstance(message, JSONRPCRequest):
                            response = await self._handle_request(message)
                            if response:  # Don't include responses for notifications
                                responses.append(response)
                        elif isinstance(message, JSONRPCNotification):
                            await self._handle_notification(message)

                    return JSONResponse(content=[r.model_dump() for r in responses])

                else:
                    # Handle single request
                    message = JSONRPCHandler.parse_message(body)

                    if isinstance(message, JSONRPCRequest):
                        response = await self._handle_request(message)
                        return JSONResponse(content=response.model_dump() if response else {})
                    elif isinstance(message, JSONRPCNotification):
                        await self._handle_notification(message)
                        return JSONResponse(content={})
                    else:
                        error_response = JSONRPCHandler.create_error_response(
                            None, INVALID_REQUEST, "Invalid JSON-RPC message type"
                        )
                        return JSONResponse(content=error_response.model_dump(), status_code=400)

            except ValueError as e:
                error_response = JSONRPCHandler.create_error_response(
                    None, PARSE_ERROR, f"Parse error: {str(e)}"
                )
                return JSONResponse(content=error_response.model_dump(), status_code=400)
            except Exception as e:
                logger.error(event="jsonrpc_handler_error", error=str(e))
                error_response = JSONRPCHandler.create_error_response(
                    None, INTERNAL_ERROR, "Internal server error"
                )
                return JSONResponse(content=error_response.model_dump(), status_code=500)

        @self.router.websocket("/notifications")
        async def websocket_notifications(websocket: WebSocket):
            """
            WebSocket endpoint for real-time notifications.

            Clients can connect here to receive tool list change notifications
            and other MCP notifications in real-time.
            """
            await websocket.accept()
            self.state.notification_subscribers.add(websocket)

            try:
                while True:
                    # Keep connection alive and handle ping/pong
                    try:
                        await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.send_json(
                            {
                                "jsonrpc": "2.0",
                                "method": "ping",
                                "params": {"timestamp": datetime.utcnow().isoformat()},
                            }
                        )

            except WebSocketDisconnect:
                self.state.notification_subscribers.discard(websocket)
                logger.info(
                    event="websocket_disconnected",
                    subscribers_count=len(self.state.notification_subscribers),
                )

        # No legacy endpoints - full MCP 2025 compliance only

    async def _handle_request(
        self, request: JSONRPCRequest
    ) -> Optional[JSONRPCResponse | JSONRPCErrorResponse]:
        """Handle a JSON-RPC request."""
        try:
            logger.debug(event="jsonrpc_request", method=request.method, id=request.id)

            # Route to appropriate handler based on method
            if request.method == MCPMethods.INITIALIZE:
                return await self._handle_initialize(request)
            elif request.method == MCPMethods.PING:
                return await self._handle_ping(request)
            elif request.method == MCPMethods.TOOLS_LIST:
                return await self._handle_tools_list(request)
            elif request.method == MCPMethods.TOOLS_CALL:
                return await self._handle_tools_call(request)
            else:
                return JSONRPCHandler.create_error_response(
                    request.id, METHOD_NOT_FOUND, f"Method '{request.method}' not found"
                )

        except Exception as e:
            logger.error(event="request_handler_error", method=request.method, error=str(e))
            return JSONRPCHandler.create_error_response(
                request.id, INTERNAL_ERROR, f"Internal error: {str(e)}"
            )

    async def _handle_notification(self, notification: JSONRPCNotification) -> None:
        """Handle a JSON-RPC notification."""
        try:
            logger.debug(event="jsonrpc_notification", method=notification.method)

            if notification.method == MCPMethods.INITIALIZED:
                await self._handle_initialized(notification)
            elif notification.method == MCPMethods.CANCEL:
                await self._handle_cancel(notification)
            else:
                logger.warning(event="unknown_notification", method=notification.method)

        except Exception as e:
            logger.error(
                event="notification_handler_error", method=notification.method, error=str(e)
            )

    async def _handle_initialize(
        self, request: JSONRPCRequest
    ) -> JSONRPCResponse | JSONRPCErrorResponse:
        """Handle initialize request - capability negotiation."""
        try:
            if not request.params:
                return JSONRPCHandler.create_error_response(
                    request.id, INVALID_PARAMS, "Initialize requires params"
                )

            # Parse initialize parameters with proper client capabilities model
            params_dict = request.params

            # Handle potential differences in capabilities model
            try:
                params = MCPInitializeParams.model_validate(params_dict)
            except Exception:
                # Fallback for compatibility
                from .jsonrpc import MCPClientCapabilities

                client_caps = MCPClientCapabilities.model_validate(
                    params_dict.get("capabilities", {})
                )
                client_info = params_dict.get("clientInfo", {})

                params = MCPInitializeParams(
                    protocolVersion=params_dict.get("protocolVersion", "2025-06-18"),
                    capabilities=client_caps,
                    clientInfo=client_info,
                )

            # Validate protocol version
            if params.protocolVersion != MCP_PROTOCOL_VERSION:
                logger.warning(
                    event="protocol_version_mismatch",
                    client_version=params.protocolVersion,
                    server_version=MCP_PROTOCOL_VERSION,
                )

            # Create initialize result with enhanced capabilities
            result = MCPInitializeResult(
                protocolVersion=MCP_PROTOCOL_VERSION,
                capabilities=self.capabilities,
                serverInfo=self.server_info,
                instructions=(
                    "This MCP server provides AI configuration tools and supports multiple content types. "
                    "Use the 'ai_configure' tool to modify AI model parameters using natural language commands. "
                    "The server supports text, image, audio, and resource content types in tool responses."
                ),
            )

            logger.info(
                event="client_initialized",
                client_info=params.clientInfo.model_dump(),
                client_capabilities=params.capabilities.model_dump(),
                protocol_version=params.protocolVersion,
            )

            return JSONRPCHandler.create_response(request.id, result.model_dump())

        except Exception as e:
            return JSONRPCHandler.create_error_response(
                request.id, INVALID_PARAMS, f"Invalid initialize params: {str(e)}"
            )

    async def _handle_ping(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle ping request."""
        return JSONRPCHandler.create_response(
            request.id,
            {"timestamp": datetime.utcnow().isoformat(), "server": self.server_info.model_dump()},
        )

    async def _handle_tools_list(
        self, request: JSONRPCRequest
    ) -> JSONRPCResponse | JSONRPCErrorResponse:
        """Handle tools/list request with cursor-based pagination."""
        try:
            params = MCPToolsListParams.model_validate(request.params or {})

            # Get all tools
            all_tools = await self.tool_registry.list_tools()

            # Convert tools to MCP format
            mcp_tools = []
            for tool in all_tools:
                mcp_tool = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": self._convert_tool_parameters_to_schema(tool),
                }
                mcp_tools.append(mcp_tool)

            # Handle pagination
            cursor_index = 0
            if params.cursor:
                try:
                    cursor_index = int(params.cursor)
                except ValueError:
                    return JSONRPCHandler.create_error_response(
                        request.id, INVALID_PARAMS, "Invalid cursor format"
                    )

            # Paginate results
            page_size = DEFAULT_PAGE_SIZE
            start_index = cursor_index
            end_index = start_index + page_size

            paginated_tools = mcp_tools[start_index:end_index]
            next_cursor = str(end_index) if end_index < len(mcp_tools) else None

            result = MCPToolsListResult(tools=paginated_tools, nextCursor=next_cursor)

            if should_log_adapter_details():
                logger.info(
                    event="tools_listed",
                    total_tools=len(all_tools),
                    returned_tools=len(paginated_tools),
                    cursor=params.cursor,
                    next_cursor=next_cursor,
                )

            return JSONRPCHandler.create_response(request.id, result.model_dump())

        except Exception as e:
            return JSONRPCHandler.create_error_response(
                request.id, INTERNAL_ERROR, f"Failed to list tools: {str(e)}"
            )

    async def _handle_tools_call(
        self, request: JSONRPCRequest
    ) -> JSONRPCResponse | JSONRPCErrorResponse:
        """Handle tools/call request."""
        try:
            if not request.params:
                return JSONRPCHandler.create_error_response(
                    request.id, INVALID_PARAMS, "Tool call requires params"
                )

            params = MCPToolsCallParams.model_validate(request.params)

            # Log the tool call request JSON
            log_tool_call_json(
                event="direct_mcp_tool_request",
                json_data=request.model_dump(),
                direction="incoming",
            )

            # Execute tool through registry
            execution = await self.tool_registry.execute_tool(
                tool_name=params.name, arguments=params.arguments or {}
            )

            if execution.success:
                # Convert result to MCP format with multi-type support
                content = []
                structured_content = None

                # Add main result as text
                if "message" in execution.result:
                    content.append({"type": ContentType.TEXT, "text": execution.result["message"]})

                # Add structured data if present
                if "data" in execution.result:
                    data = execution.result["data"]
                    if isinstance(data, str):
                        content.append({"type": ContentType.TEXT, "text": data})
                    elif isinstance(data, dict):
                        # Structured content for better client processing
                        structured_content = data
                        content.append({"type": ContentType.TEXT, "text": str(data)})
                    else:
                        content.append({"type": ContentType.TEXT, "text": str(data)})

                # Support for future multi-type results (images, audio, resources)
                if "image" in execution.result:
                    image_data = execution.result["image"]
                    content.append(
                        {
                            "type": ContentType.IMAGE,
                            "data": image_data["data"],
                            "mimeType": image_data.get("mimeType", "image/png"),
                        }
                    )

                if "audio" in execution.result:
                    audio_data = execution.result["audio"]
                    content.append(
                        {
                            "type": ContentType.AUDIO,
                            "data": audio_data["data"],
                            "mimeType": audio_data.get("mimeType", "audio/wav"),
                        }
                    )

                if "resource" in execution.result:
                    content.append(
                        {"type": ContentType.RESOURCE, "resource": execution.result["resource"]}
                    )

                if "resource_link" in execution.result:
                    link_data = execution.result["resource_link"]
                    content.append(
                        {
                            "type": ContentType.RESOURCE_LINK,
                            "uri": link_data["uri"],
                            "name": link_data.get("name"),
                            "description": link_data.get("description"),
                            "mimeType": link_data.get("mimeType"),
                        }
                    )

                # Create result with structured content support
                result_data = {"content": content, "isError": False}

                # Add structured content if available (MCP 2025 enhancement)
                if structured_content:
                    result_data["structuredContent"] = structured_content

                response = JSONRPCHandler.create_response(request.id, result_data)

                # Log the tool call response JSON
                log_tool_call_json(
                    event="direct_mcp_tool_response",
                    json_data=response.model_dump(),
                    direction="outgoing",
                )

                return response

            else:
                # Tool execution failed
                result = MCPToolsCallResult(
                    content=[{"type": "text", "text": execution.error or "Tool execution failed"}],
                    isError=True,
                )

                logger.warning(
                    event="tool_execution_failed", tool_name=params.name, error=execution.error
                )

                return JSONRPCHandler.create_response(request.id, result.model_dump())

        except Exception as e:
            logger.error(event="tool_call_error", error=str(e))
            return JSONRPCHandler.create_error_response(
                request.id, MCP_TOOL_EXECUTION_ERROR, f"Tool execution error: {str(e)}"
            )

    async def _handle_initialized(self, notification: JSONRPCNotification) -> None:
        """Handle initialized notification from client."""
        # Mark client as initialized (we could track client IDs here)
        logger.info(event="client_ready", message="Client has completed initialization")

    async def _handle_cancel(self, notification: JSONRPCNotification) -> None:
        """Handle cancellation notification."""
        if notification.params and "requestId" in notification.params:
            request_id = notification.params["requestId"]
            logger.info(event="request_cancelled", request_id=request_id)
            # Here we would cancel any ongoing operations for this request

    def _convert_tool_parameters_to_schema(self, tool: Tool) -> Dict[str, Any]:
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
                items_schema: Dict[str, Any] = {
                    "type": param.items.type.value,
                    "description": param.items.description,
                }
                # Add enum if the items have it
                if param.items.enum:
                    items_schema["enum"] = param.items.enum
                prop_schema["items"] = items_schema

            properties[param.name] = prop_schema

            if param.required:
                required.append(param.name)

        return {"type": "object", "properties": properties, "required": required}

    async def notify_tools_changed(self) -> None:
        """Send tools list changed notification to all connected clients."""
        self.state.tools_version += 1

        notification = JSONRPCHandler.create_notification(
            method=MCPMethods.TOOLS_LIST_CHANGED, params={"version": self.state.tools_version}
        )

        # Send to all WebSocket subscribers
        disconnected = set()
        for websocket in self.state.notification_subscribers:
            try:
                await websocket.send_json(notification.model_dump())
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.state.notification_subscribers.discard(websocket)

        logger.info(
            event="tools_change_notification_sent",
            subscribers_notified=len(self.state.notification_subscribers) - len(disconnected),
            tools_version=self.state.tools_version,
        )

    def get_router(self) -> APIRouter:
        """Get the FastAPI router for the MCP server."""
        return self.router

    async def register_tool(self, tool: Tool) -> None:
        """Register a tool and notify clients of the change."""
        await self.tool_registry.register_tool(tool)
        await self.notify_tools_changed()

        logger.info(event="tool_registered_with_notification", tool_name=tool.name)

    async def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool and notify clients of the change."""
        success = await self.tool_registry.unregister_tool(tool_name)

        if success:
            await self.notify_tools_changed()
            logger.info(event="tool_unregistered_with_notification", tool_name=tool_name)

        return success

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the MCP server."""
        tools = await self.tool_registry.list_tools()

        return {
            "status": "healthy",
            "protocol_version": MCP_PROTOCOL_VERSION,
            "tools_count": len(tools),
            "notification_subscribers": len(self.state.notification_subscribers),
            "tools_version": self.state.tools_version,
            "capabilities": self.capabilities.model_dump(),
            "endpoints": {"jsonrpc": "/mcp/jsonrpc", "notifications": "/mcp/notifications"},
        }

    # Configuration Management Methods (Phase 2)

    async def get_active_provider_config(self) -> Dict[str, Any]:
        """
        Get complete configuration for the currently active provider.
        This is the primary method for getting LLM configuration.

        Returns:
            Complete provider configuration including model, parameters, etc.

        Raises:
            RuntimeError: If configuration cannot be loaded
        """
        try:
            # Load configuration if not cached
            if self.config_cache is None:
                self.config_cache = self.config_persistence.load_config()

            # Get provider configuration
            provider_config = self.config_cache.get("provider", {})
            active_provider = provider_config.get("active", "openai")

            # Get model config for active provider
            models = provider_config.get("models", {})
            active_model_config = models.get(active_provider, {})

            result = {
                "provider": active_provider,
                "model": active_model_config.get("model", "gpt-4o-mini"),
                "temperature": active_model_config.get("temperature", 0.7),
                "max_tokens": active_model_config.get("max_tokens"),
                "system_prompt": active_model_config.get(
                    "system_prompt", "You are a helpful AI assistant."
                ),
            }

            logger.debug(
                event="active_provider_config_retrieved",
                provider=result.get("provider"),
                model=result.get("model"),
                parameters=list(result.keys()),
            )

            return result

        except Exception as e:
            logger.error(event="get_active_provider_config_failed", error=str(e))
            raise RuntimeError(f"Failed to get active provider configuration: {str(e)}")

    async def set_provider_parameter(self, provider: str, param_name: str, value: Any) -> bool:
        """
        Update a specific parameter for a provider.

        Args:
            provider: Provider name (openai, anthropic, gemini, openrouter)
            param_name: Parameter to update (temperature, max_tokens, etc.)
            value: New parameter value

        Returns:
            True if update successful, False otherwise

        Raises:
            ValueError: If provider or parameter is invalid
            RuntimeError: If update fails
        """
        try:
            # Validate provider exists
            available_providers = await self.get_available_providers()
            if provider not in available_providers:
                raise ValueError(f"Invalid provider '{provider}'. Available: {available_providers}")

            # Get parameter constraints for validation
            constraints = await self.get_parameter_constraints(provider)
            if param_name not in constraints:
                raise ValueError(f"Invalid parameter '{param_name}' for provider '{provider}'")

            # Validate parameter value
            constraint = constraints[param_name]
            validated_value = self._validate_parameter_value(value, constraint)

            # Update configuration in cache and persist
            if self.config_cache is None:
                self.config_cache = self.config_persistence.load_config()

            # Update the parameter
            if provider not in self.config_cache["provider"]["models"]:
                self.config_cache["provider"]["models"][provider] = {}

            self.config_cache["provider"]["models"][provider][param_name] = validated_value

            # Save to file
            success = self.config_persistence.save_config(self.config_cache)

            if success:
                # Notify configuration change
                await self._notify_configuration_changed(provider, param_name, validated_value)

                logger.info(
                    event="provider_parameter_updated",
                    provider=provider,
                    parameter=param_name,
                    old_value=constraint.get("current_value"),
                    new_value=validated_value,
                )

                return True
            else:
                raise RuntimeError("Configuration update failed")

        except Exception as e:
            logger.error(
                event="set_provider_parameter_failed",
                provider=provider,
                parameter=param_name,
                value=value,
                error=str(e),
            )
            if isinstance(e, (ValueError, RuntimeError)):
                raise
            raise RuntimeError(f"Failed to set parameter: {str(e)}")

    async def switch_active_provider(self, provider: str) -> bool:
        """
        Switch the active provider.

        Args:
            provider: Provider name to switch to

        Returns:
            True if switch successful, False otherwise

        Raises:
            ValueError: If provider is invalid
            RuntimeError: If switch fails
        """
        try:
            # Validate provider exists
            available_providers = await self.get_available_providers()
            if provider not in available_providers:
                raise ValueError(f"Invalid provider '{provider}'. Available: {available_providers}")

            # Get current provider for logging
            current_config = await self.get_active_provider_config()
            current_provider = current_config.get("provider", "unknown")

            # Update configuration in cache and persist
            if self.config_cache is None:
                self.config_cache = self.config_persistence.load_config()

            # Switch provider
            self.config_cache["provider"]["active"] = provider

            # Save to file
            success = self.config_persistence.save_config(self.config_cache)

            if success:
                # Notify configuration change
                await self._notify_provider_switched(current_provider, provider)

                logger.info(
                    event="active_provider_switched",
                    old_provider=current_provider,
                    new_provider=provider,
                )

                return True
            else:
                raise RuntimeError("Provider switch failed")

        except Exception as e:
            logger.error(event="switch_active_provider_failed", provider=provider, error=str(e))
            if isinstance(e, (ValueError, RuntimeError)):
                raise
            raise RuntimeError(f"Failed to switch provider: {str(e)}")

    async def get_available_models(self, provider: str) -> Dict[str, Any]:
        """
        Get available models for a specific provider.

        Args:
            provider: Provider name

        Returns:
            Dictionary with available models and their info

        Raises:
            ValueError: If provider is invalid
        """
        try:
            # Get models from parameter schemas
            if provider not in PopularModels.PHASE_1_MODELS:
                raise ValueError(f"Provider '{provider}' not supported")

            models = PopularModels.PHASE_1_MODELS[provider]

            # Format response with model details
            result = {"provider": provider, "models": []}

            for model_name in models:
                model_info = {
                    "name": model_name,
                    "supported": PopularModels.is_supported_model(provider, model_name),
                    "schema_available": ModelParameterSchemas.has_schema(provider, model_name),
                }
                result["models"].append(model_info)

            logger.debug(
                event="available_models_retrieved", provider=provider, model_count=len(models)
            )

            return result

        except Exception as e:
            logger.error(event="get_available_models_failed", provider=provider, error=str(e))
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Failed to get available models: {str(e)}")

    async def get_parameter_constraints(self, provider: str) -> Dict[str, Any]:
        """
        Get parameter constraints for a specific provider.

        Args:
            provider: Provider name

        Returns:
            Dictionary with parameter constraints and current values

        Raises:
            ValueError: If provider is invalid
        """
        try:
            # Get current config to determine model
            current_config = await self.get_active_provider_config()
            model = current_config.get("model", "")

            # Get parameter schema
            schema = ModelParameterSchemas.get_model_schema(provider, model)

            # Build constraints with current values
            constraints = {}
            for param_name, constraint in schema.items():
                current_value = current_config.get(param_name, constraint.default)

                constraints[param_name] = {
                    "type": constraint.param_type.value,
                    "description": constraint.description,
                    "min_value": constraint.min_value,
                    "max_value": constraint.max_value,
                    "enum_values": constraint.enum_values,
                    "default": constraint.default,
                    "current_value": current_value,
                    "required": constraint.required,
                }

            logger.debug(
                event="parameter_constraints_retrieved",
                provider=provider,
                model=model,
                parameter_count=len(constraints),
            )

            return constraints

        except Exception as e:
            logger.error(event="get_parameter_constraints_failed", provider=provider, error=str(e))
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Failed to get parameter constraints: {str(e)}")

    async def reset_to_defaults(self, provider: str) -> bool:
        """
        Reset provider configuration to defaults.

        Args:
            provider: Provider name to reset

        Returns:
            True if reset successful, False otherwise

        Raises:
            ValueError: If provider is invalid
            RuntimeError: If reset fails
        """
        try:
            # Validate provider
            available_providers = await self.get_available_providers()
            if provider not in available_providers:
                raise ValueError(f"Invalid provider '{provider}'. Available: {available_providers}")

            # Get default values
            constraints = await self.get_parameter_constraints(provider)
            defaults = {}

            for param_name, constraint in constraints.items():
                if constraint["default"] is not None:
                    defaults[param_name] = constraint["default"]

            # Load configuration if not cached
            if self.config_cache is None:
                self.config_cache = self.config_persistence.load_config()

            # Apply defaults
            success_count = 0
            for param_name, default_value in defaults.items():
                try:
                    # Update the parameter
                    if provider not in self.config_cache["provider"]["models"]:
                        self.config_cache["provider"]["models"][provider] = {}

                    self.config_cache["provider"]["models"][provider][param_name] = default_value
                    success_count += 1
                except Exception as e:
                    logger.warning(
                        event="default_parameter_update_failed",
                        provider=provider,
                        parameter=param_name,
                        error=str(e),
                    )

            # Save configuration if any defaults were applied
            if success_count > 0:
                success = self.config_persistence.save_config(self.config_cache)
                if not success:
                    raise RuntimeError("Failed to save configuration")

            if success_count > 0:
                # Notify configuration reset
                await self._notify_configuration_reset(provider, defaults)

                logger.info(
                    event="provider_reset_to_defaults",
                    provider=provider,
                    parameters_reset=success_count,
                    total_parameters=len(defaults),
                )

                return True
            else:
                raise RuntimeError("No parameters were reset")

        except Exception as e:
            logger.error(event="reset_to_defaults_failed", provider=provider, error=str(e))
            if isinstance(e, (ValueError, RuntimeError)):
                raise
            raise RuntimeError(f"Failed to reset to defaults: {str(e)}")

    async def get_available_providers(self) -> list[str]:
        """
        Get list of available providers.

        Returns:
            List of provider names
        """
        return list(PopularModels.PHASE_1_MODELS.keys())

    def _validate_parameter_value(self, value: Any, constraint: Dict[str, Any]) -> Any:
        """
        Validate a parameter value against its constraints.

        Args:
            value: Value to validate
            constraint: Constraint dictionary

        Returns:
            Validated value

        Raises:
            ValueError: If value is invalid
        """
        try:
            # Type validation
            param_type = constraint["type"]
            if param_type == "integer" and not isinstance(value, int):
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                else:
                    raise ValueError(f"Expected integer, got {type(value).__name__}")
            elif param_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Expected number, got {type(value).__name__}")
            elif param_type == "string" and not isinstance(value, str):
                raise ValueError(f"Expected string, got {type(value).__name__}")

            # Range validation
            if constraint["min_value"] is not None and isinstance(value, (int, float)):
                if value < constraint["min_value"]:
                    raise ValueError(f"Value {value} below minimum {constraint['min_value']}")

            if constraint["max_value"] is not None and isinstance(value, (int, float)):
                if value > constraint["max_value"]:
                    raise ValueError(f"Value {value} above maximum {constraint['max_value']}")

            # Enum validation
            if constraint["enum_values"] and value not in constraint["enum_values"]:
                raise ValueError(
                    f"Value {value} not in allowed values: {constraint['enum_values']}"
                )

            return value

        except Exception as e:
            logger.error(
                event="parameter_validation_failed",
                value=value,
                constraint=constraint,
                error=str(e),
            )
            raise ValueError(f"Parameter validation failed: {str(e)}")

    async def _notify_configuration_changed(
        self, provider: str, param_name: str, value: Any
    ) -> None:
        """Send configuration change notification to WebSocket subscribers."""
        notification = JSONRPCHandler.create_notification(
            method="configuration/changed",
            params={
                "provider": provider,
                "parameter": param_name,
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        await self._send_notification_to_subscribers(notification)

    async def _notify_provider_switched(self, old_provider: str, new_provider: str) -> None:
        """Send provider switch notification to WebSocket subscribers."""
        notification = JSONRPCHandler.create_notification(
            method="configuration/provider_switched",
            params={
                "old_provider": old_provider,
                "new_provider": new_provider,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        await self._send_notification_to_subscribers(notification)

    async def _notify_configuration_reset(self, provider: str, defaults: Dict[str, Any]) -> None:
        """Send configuration reset notification to WebSocket subscribers."""
        notification = JSONRPCHandler.create_notification(
            method="configuration/reset",
            params={
                "provider": provider,
                "defaults": defaults,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        await self._send_notification_to_subscribers(notification)

    async def _send_notification_to_subscribers(self, notification: JSONRPCNotification) -> None:
        """Send notification to all WebSocket subscribers."""
        disconnected = set()
        for websocket in self.state.notification_subscribers:
            try:
                await websocket.send_json(notification.model_dump())
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.state.notification_subscribers.discard(websocket)

        logger.debug(
            event="configuration_notification_sent",
            method=notification.method,
            subscribers_notified=len(self.state.notification_subscribers) - len(disconnected),
        )

    def _register_configuration_tools(self) -> None:
        """Register all AI configuration tools."""
        from .tools import (
            AIConfigurationTool,
            ShowConfigTool,
            ListModelsTool,
            SwitchProviderTool,
            ParameterInfoTool,
            ResetConfigTool,
        )

        # Initialize tools with dependencies
        tools = [
            AIConfigurationTool(self),
            ShowConfigTool(self),
            ListModelsTool(self),
            SwitchProviderTool(self),
            ParameterInfoTool(self),
            ResetConfigTool(self),
        ]

        # Register each tool synchronously by directly calling the registry methods
        for tool_handler in tools:
            tool_def = tool_handler.get_tool_definition()

            # Register tool definition directly (synchronous)
            self.tool_registry.tools[tool_def.name] = tool_def
            self.tool_registry.handlers[tool_def.name] = tool_handler

            logger.info(
                event="configuration_tool_registered",
                tool_name=tool_def.name,
                category=tool_def.category,
            )

        logger.info(
            event="all_configuration_tools_registered",
            tools_count=len(tools),
        )


# Global MCP server instance
_mcp2025_server: Optional[MCP2025Server] = None


def get_mcp2025_server() -> MCP2025Server:
    """Get or create the global MCP 2025 server instance."""
    global _mcp2025_server
    if _mcp2025_server is None:
        _mcp2025_server = MCP2025Server()
    return _mcp2025_server
