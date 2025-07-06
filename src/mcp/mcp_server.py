"""
Standard MCP HTTP Server Implementation

This module implements the standard Model Context Protocol (MCP) HTTP endpoints
following the official MCP 2025 specification for tool discovery and execution.

Standard Endpoints:
- POST /tools/list - Discover available tools/capabilities (MCP 2025 spec)
- POST /tools/call - Execute a specific tool with parameters

This provides vendor-agnostic runtime discovery that works with any MCP client.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from common.logging import get_logger
from common.runtime_config import get_runtime_config_manager
from .tool_registry import ToolRegistry, Tool

logger = get_logger(__name__)


class MCPToolListResponse(BaseModel):
    """Standard MCP response for /tools/list endpoint."""

    tools: List[Tool]
    meta: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallRequest(BaseModel):
    """Standard MCP request for /tools/call endpoint."""

    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    """Standard MCP response for /tools/call endpoint."""

    content: List[Dict[str, Any]]
    isError: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict)


class MCPServer:
    """
    Standard MCP HTTP Server implementation.

    Provides vendor-agnostic tool discovery and execution following
    the official MCP specification.
    """

    def __init__(self):
        """Initialize the MCP server."""
        self.runtime_config_manager = get_runtime_config_manager()
        self.tool_registry = ToolRegistry(self.runtime_config_manager)

        # Initialize router
        self.router = APIRouter(prefix="/tools", tags=["MCP Tools"])
        self._setup_routes()

        logger.info(
            event="mcp_server_initialized",
            message="Standard MCP server initialized with tool registry",
            endpoints=["/tools/list", "/tools/call"],
        )

    def _setup_routes(self) -> None:
        """Setup standard MCP routes."""

        @self.router.post("/list", response_model=MCPToolListResponse)
        async def list_tools() -> MCPToolListResponse:
            """
            Standard MCP endpoint for tool discovery.

            Returns all available tools with their schemas and descriptions.
            Note: MCP 2025 specification requires POST for /tools/list
            """
            try:
                tools = await self.tool_registry.list_tools()

                logger.info(
                    event="mcp_tools_listed",
                    tool_count=len(tools),
                    tool_names=[tool.name for tool in tools],
                )

                return MCPToolListResponse(
                    tools=tools,
                    meta={
                        "server": "MCP Backend",
                        "version": "1.0.0",
                        "capabilities": ["tools", "runtime_discovery", "parameter_validation"],
                    },
                )

            except Exception as e:
                logger.error(event="mcp_tools_list_error", error=str(e))
                raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

        @self.router.post("/call", response_model=MCPToolCallResponse)
        async def call_tool(request: MCPToolCallRequest) -> MCPToolCallResponse:
            """
            Standard MCP endpoint for tool execution.

            Executes the specified tool with provided arguments.
            """
            try:
                # Execute tool through registry
                execution = await self.tool_registry.execute_tool(
                    tool_name=request.name, arguments=request.arguments
                )

                # Convert execution result to MCP format
                if execution.success:
                    content = [
                        {
                            "type": "text",
                            "text": execution.result.get("message", "Tool executed successfully"),
                        }
                    ]

                    # Add structured data if present
                    if "data" in execution.result:
                        content.append(
                            {"type": "text", "text": f"Result: {execution.result['data']}"}
                        )

                    logger.info(
                        event="mcp_tool_executed",
                        tool_name=request.name,
                        success=True,
                        execution_time_ms=execution.execution_time_ms,
                    )

                    return MCPToolCallResponse(
                        content=content,
                        isError=False,
                        meta={
                            "tool": request.name,
                            "execution_time_ms": execution.execution_time_ms,
                            "confidence": execution.result.get("confidence"),
                            "adjustments": execution.result.get("adjustments"),
                        },
                    )

                else:
                    # Tool execution failed
                    logger.warning(
                        event="mcp_tool_execution_failed",
                        tool_name=request.name,
                        error=execution.error,
                    )

                    return MCPToolCallResponse(
                        content=[
                            {"type": "text", "text": f"Tool execution failed: {execution.error}"}
                        ],
                        isError=True,
                        meta={"tool": request.name, "error": execution.error},
                    )

            except Exception as e:
                logger.error(event="mcp_tool_call_error", tool_name=request.name, error=str(e))

                return MCPToolCallResponse(
                    content=[{"type": "text", "text": f"Internal error executing tool: {str(e)}"}],
                    isError=True,
                    meta={"tool": request.name, "error": str(e)},
                )

    def get_router(self) -> APIRouter:
        """Get the FastAPI router for the MCP server."""
        return self.router

    async def register_tool(self, tool: Tool) -> None:
        """Register a new tool with the MCP server."""
        await self.tool_registry.register_tool(tool)

        logger.info(
            event="mcp_tool_registered", tool_name=tool.name, tool_description=tool.description
        )

    async def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool from the MCP server."""
        success = await self.tool_registry.unregister_tool(tool_name)

        if success:
            logger.info(event="mcp_tool_unregistered", tool_name=tool_name)
        else:
            logger.warning(
                event="mcp_tool_unregister_failed", tool_name=tool_name, reason="tool_not_found"
            )

        return success

    async def get_tool_info(self, tool_name: str) -> Optional[Tool]:
        """Get information about a specific tool."""
        return await self.tool_registry.get_tool(tool_name)

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the MCP server."""
        tools = await self.tool_registry.list_tools()

        return {
            "status": "healthy",
            "tools_count": len(tools),
            "endpoints": ["/tools/list", "/tools/call"],
            "capabilities": [
                "runtime_discovery",
                "parameter_validation",
                "vendor_agnostic_execution",
            ],
        }


# Global MCP server instance
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """Get or create the global MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server
