"""
JSON-RPC 2.0 Protocol Implementation for MCP

This module implements the JSON-RPC 2.0 message format required by the
Model Context Protocol specification. All MCP messages must be wrapped
in JSON-RPC envelopes for full compliance.

Reference: https://www.jsonrpc.org/specification
MCP Spec: https://spec.modelcontextprotocol.io/specification/2025-06-18/basic/
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel

# JSON-RPC version constant
JSONRPC_VERSION = "2.0"

# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# MCP-specific error codes
MCP_SERVER_ERROR = -32000
MCP_TOOL_NOT_FOUND = -32001
MCP_TOOL_EXECUTION_ERROR = -32002


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message (success)."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int]
    result: Any


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 response message (error)."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int, None]
    error: JSONRPCError


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification message (no response expected)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


# Union type for all JSON-RPC messages
JSONRPCMessage = Union[JSONRPCRequest, JSONRPCResponse, JSONRPCErrorResponse, JSONRPCNotification]

# Batch support (array of JSON-RPC messages)
JSONRPCBatch = List[Union[JSONRPCRequest, JSONRPCNotification]]
JSONRPCBatchResponse = List[Union[JSONRPCResponse, JSONRPCErrorResponse]]


class MCPMethods:
    """Standard MCP method names."""

    # Core protocol
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    PING = "ping"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    TOOLS_LIST_CHANGED = "notifications/tools/list_changed"

    # Resources (for future implementation)
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    RESOURCES_LIST_CHANGED = "notifications/resources/list_changed"
    RESOURCES_UPDATED = "notifications/resources/updated"

    # Prompts (for future implementation)
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    PROMPTS_LIST_CHANGED = "notifications/prompts/list_changed"

    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"
    LOGGING_MESSAGE = "notifications/message"

    # Cancellation
    CANCEL = "notifications/cancelled"

    # Progress
    PROGRESS = "notifications/progress"

    # Client features (MCP 2025)
    SAMPLING_CREATE_MESSAGE = "sampling/createMessage"
    ROOTS_LIST = "roots/list"


class MCPCapabilities(BaseModel):
    """MCP server capabilities."""

    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    completion: Optional[Dict[str, Any]] = None  # MCP 2025 addition


class MCPClientCapabilities(BaseModel):
    """MCP client capabilities."""

    experimental: Optional[Dict[str, Any]] = None
    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None
    elicitation: Optional[Dict[str, Any]] = None  # MCP 2025 addition


class MCPImplementation(BaseModel):
    """MCP implementation info."""

    name: str
    version: str


class MCPInitializeParams(BaseModel):
    """Parameters for initialize request."""

    protocolVersion: str
    capabilities: MCPClientCapabilities
    clientInfo: MCPImplementation


class MCPInitializeResult(BaseModel):
    """Result for initialize response."""

    protocolVersion: str
    capabilities: MCPCapabilities
    serverInfo: MCPImplementation
    instructions: Optional[str] = None


class MCPToolsListParams(BaseModel):
    """Parameters for tools/list request."""

    cursor: Optional[str] = None


class MCPToolsListResult(BaseModel):
    """Result for tools/list response."""

    tools: List[Dict[str, Any]]
    nextCursor: Optional[str] = None


class MCPToolsCallParams(BaseModel):
    """Parameters for tools/call request."""

    name: str
    arguments: Optional[Dict[str, Any]] = None


class MCPToolsCallResult(BaseModel):
    """Result for tools/call response."""

    content: List[Dict[str, Any]]
    isError: bool = False
    # MCP 2025 enhancement: support for structured results
    structuredContent: Optional[Dict[str, Any]] = None


# MCP 2025 Content Types for multi-type tool results
class MCPContentTypes:
    """Standard MCP content types."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    RESOURCE = "resource"
    RESOURCE_LINK = "resource_link"


class MCPTextContent(BaseModel):
    """Text content for tool results."""

    type: str = MCPContentTypes.TEXT
    text: str


class MCPImageContent(BaseModel):
    """Image content for tool results."""

    type: str = MCPContentTypes.IMAGE
    data: str  # base64 encoded
    mimeType: str


class MCPAudioContent(BaseModel):
    """Audio content for tool results."""

    type: str = MCPContentTypes.AUDIO
    data: str  # base64 encoded
    mimeType: str


class MCPResourceContent(BaseModel):
    """Resource content for tool results."""

    type: str = MCPContentTypes.RESOURCE
    resource: Dict[str, Any]  # Resource object with uri, text, etc.


class MCPResourceLinkContent(BaseModel):
    """Resource link content for tool results."""

    type: str = MCPContentTypes.RESOURCE_LINK
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    mimeType: Optional[str] = None


class JSONRPCHandler:
    """Handler for JSON-RPC message processing."""

    @staticmethod
    def create_request(
        id: Union[str, int], method: str, params: Optional[Dict[str, Any]] = None
    ) -> JSONRPCRequest:
        """Create a JSON-RPC request."""
        return JSONRPCRequest(id=id, method=method, params=params)

    @staticmethod
    def create_response(id: Union[str, int], result: Any) -> JSONRPCResponse:
        """Create a JSON-RPC success response."""
        return JSONRPCResponse(id=id, result=result)

    @staticmethod
    def create_error_response(
        id: Union[str, int, None], code: int, message: str, data: Optional[Any] = None
    ) -> JSONRPCErrorResponse:
        """Create a JSON-RPC error response."""
        error = JSONRPCError(code=code, message=message, data=data)
        return JSONRPCErrorResponse(id=id, error=error)

    @staticmethod
    def create_notification(
        method: str, params: Optional[Dict[str, Any]] = None
    ) -> JSONRPCNotification:
        """Create a JSON-RPC notification."""
        return JSONRPCNotification(method=method, params=params)

    @staticmethod
    def parse_message(data: Dict[str, Any]) -> JSONRPCMessage:
        """Parse a raw JSON object into a JSON-RPC message."""
        if "id" in data:
            if "method" in data:
                # Request
                return JSONRPCRequest.model_validate(data)
            elif "result" in data:
                # Success response
                return JSONRPCResponse.model_validate(data)
            elif "error" in data:
                # Error response
                return JSONRPCErrorResponse.model_validate(data)
        else:
            # Notification
            return JSONRPCNotification.model_validate(data)

        raise ValueError(f"Invalid JSON-RPC message: {data}")

    @staticmethod
    def is_batch(data: Any) -> bool:
        """Check if the data represents a JSON-RPC batch."""
        return isinstance(data, list)

    @staticmethod
    def validate_batch(data: List[Any]) -> JSONRPCBatch:
        """Validate and parse a JSON-RPC batch."""
        batch = []
        for item in data:
            if isinstance(item, dict):
                message = JSONRPCHandler.parse_message(item)
                if isinstance(message, (JSONRPCRequest, JSONRPCNotification)):
                    batch.append(message)
                else:
                    raise ValueError(f"Invalid message in batch: {item}")
            else:
                raise ValueError(f"Invalid batch item: {item}")
        return batch
