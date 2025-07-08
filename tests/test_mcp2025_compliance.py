"""
Tests for MCP 2025 Compliance Features

Tests the JSON-RPC protocol layer, cursor pagination, capabilities handshake,
change notifications, and multi-type tool results.
"""

import pytest
from unittest.mock import AsyncMock, patch

from mcp.jsonrpc import (
    JSONRPCHandler,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCErrorResponse,
    JSONRPCNotification,
    MCPMethods,
    MCPImplementation,
    MCPInitializeParams,
    MCPClientCapabilities,
)
from mcp.mcp2025_server import MCP2025Server


class TestJSONRPCProtocol:
    """Test JSON-RPC 2.0 protocol compliance."""

    def test_create_request(self):
        """Test JSON-RPC request creation."""
        request = JSONRPCHandler.create_request(
            id="test-123", method="test/method", params={"param1": "value1"}
        )

        assert request.jsonrpc == "2.0"
        assert request.id == "test-123"
        assert request.method == "test/method"
        assert request.params == {"param1": "value1"}

    def test_create_response(self):
        """Test JSON-RPC response creation."""
        response = JSONRPCHandler.create_response(id="test-123", result={"success": True})

        assert response.jsonrpc == "2.0"
        assert response.id == "test-123"
        assert response.result == {"success": True}

    def test_create_error_response(self):
        """Test JSON-RPC error response creation."""
        error_response = JSONRPCHandler.create_error_response(
            id="test-123", code=-32602, message="Invalid params"
        )

        assert error_response.jsonrpc == "2.0"
        assert error_response.id == "test-123"
        assert error_response.error.code == -32602
        assert error_response.error.message == "Invalid params"

    def test_create_notification(self):
        """Test JSON-RPC notification creation."""
        notification = JSONRPCHandler.create_notification(
            method="test/notification", params={"event": "test"}
        )

        assert notification.jsonrpc == "2.0"
        assert notification.method == "test/notification"
        assert notification.params == {"event": "test"}
        # Notifications don't have IDs
        assert not hasattr(notification, "id")

    def test_parse_message_request(self):
        """Test parsing JSON-RPC request message."""
        data = {"jsonrpc": "2.0", "id": "123", "method": "test/method", "params": {"test": True}}

        message = JSONRPCHandler.parse_message(data)
        assert isinstance(message, JSONRPCRequest)
        assert message.id == "123"
        assert message.method == "test/method"

    def test_parse_message_notification(self):
        """Test parsing JSON-RPC notification message."""
        data = {"jsonrpc": "2.0", "method": "test/notification", "params": {"event": "test"}}

        message = JSONRPCHandler.parse_message(data)
        assert isinstance(message, JSONRPCNotification)
        assert message.method == "test/notification"

    def test_batch_detection(self):
        """Test batch request detection."""
        single_request = {"jsonrpc": "2.0", "id": "1", "method": "test"}
        batch_request = [
            {"jsonrpc": "2.0", "id": "1", "method": "test1"},
            {"jsonrpc": "2.0", "id": "2", "method": "test2"},
        ]

        assert not JSONRPCHandler.is_batch(single_request)
        assert JSONRPCHandler.is_batch(batch_request)


class TestCapabilitiesHandshake:
    """Test MCP capabilities negotiation and handshake."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for testing."""
        return MCP2025Server()

    @pytest.mark.asyncio
    async def test_initialize_request(self, mcp_server):
        """Test initialize request handling."""
        # Create initialize request
        client_caps = MCPClientCapabilities(roots={"listChanged": True}, sampling={})

        client_info = MCPImplementation(name="TestClient", version="1.0.0")

        params = MCPInitializeParams(
            protocolVersion="2025-06-18", capabilities=client_caps, clientInfo=client_info
        )

        request = JSONRPCHandler.create_request(
            id="init-1", method=MCPMethods.INITIALIZE, params=params.model_dump()
        )

        # Handle request
        response = await mcp_server._handle_request(request)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == "init-1"

        # Validate response structure
        result = response.result
        assert result["protocolVersion"] == "2025-06-18"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "MCP Backend Server"

    @pytest.mark.asyncio
    async def test_capabilities_declaration(self, mcp_server):
        """Test that server declares correct capabilities."""
        assert mcp_server.capabilities.tools is not None
        assert mcp_server.capabilities.tools.get("listChanged") is True
        assert mcp_server.capabilities.logging is not None

    @pytest.mark.asyncio
    async def test_initialized_notification(self, mcp_server):
        """Test initialized notification handling."""
        notification = JSONRPCHandler.create_notification(method=MCPMethods.INITIALIZED)

        # Should not raise exception
        await mcp_server._handle_notification(notification)


class TestCursorPagination:
    """Test cursor-based pagination for tools/list."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for testing."""
        return MCP2025Server()

    @pytest.mark.asyncio
    async def test_tools_list_no_cursor(self, mcp_server):
        """Test tools/list without cursor (first page)."""
        request = JSONRPCHandler.create_request(
            id="list-1", method=MCPMethods.TOOLS_LIST, params={}
        )

        response = await mcp_server._handle_request(request)

        assert isinstance(response, JSONRPCResponse)
        result = response.result

        assert "tools" in result
        assert isinstance(result["tools"], list)
        # nextCursor should be None for small tool sets
        assert result.get("nextCursor") is None

    @pytest.mark.asyncio
    async def test_tools_list_with_cursor(self, mcp_server):
        """Test tools/list with cursor pagination."""
        # First, we'd need to mock a large tool set
        with patch.object(mcp_server.tool_registry, "list_tools") as mock_list:
            # Create enough tools to trigger pagination
            mock_tools = []
            for i in range(100):  # More than DEFAULT_PAGE_SIZE (50)
                mock_tool = AsyncMock()
                mock_tool.name = f"tool_{i}"
                mock_tool.description = f"Test tool {i}"
                mock_tool.parameters = []
                mock_tools.append(mock_tool)

            mock_list.return_value = mock_tools

            # Request first page
            request = JSONRPCHandler.create_request(
                id="list-1", method=MCPMethods.TOOLS_LIST, params={}
            )

            response = await mcp_server._handle_request(request)

            assert isinstance(response, JSONRPCResponse)
            result = response.result

            assert len(result["tools"]) == 50  # DEFAULT_PAGE_SIZE
            assert result["nextCursor"] is not None

            # Request second page
            request2 = JSONRPCHandler.create_request(
                id="list-2", method=MCPMethods.TOOLS_LIST, params={"cursor": result["nextCursor"]}
            )

            response2 = await mcp_server._handle_request(request2)

            assert isinstance(response2, JSONRPCResponse)
            result2 = response2.result

            assert len(result2["tools"]) == 50  # Remaining tools
            assert result2["nextCursor"] is None  # No more pages

    @pytest.mark.asyncio
    async def test_invalid_cursor(self, mcp_server):
        """Test handling of invalid cursor."""
        request = JSONRPCHandler.create_request(
            id="list-1", method=MCPMethods.TOOLS_LIST, params={"cursor": "invalid-cursor"}
        )

        response = await mcp_server._handle_request(request)

        assert isinstance(response, JSONRPCErrorResponse)
        assert "Invalid cursor format" in response.error.message


class TestChangeNotifications:
    """Test tool list change notifications."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for testing."""
        return MCP2025Server()

    @pytest.mark.asyncio
    async def test_tools_change_notification(self, mcp_server):
        """Test that tool changes trigger notifications."""
        # Mock WebSocket subscribers
        mock_websocket = AsyncMock()
        mcp_server.state.notification_subscribers.add(mock_websocket)

        # Trigger tool change notification
        await mcp_server.notify_tools_changed()

        # Verify notification was sent
        mock_websocket.send_json.assert_called_once()

        # Verify notification format
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["jsonrpc"] == "2.0"
        assert call_args["method"] == MCPMethods.TOOLS_LIST_CHANGED
        assert "params" in call_args
        assert "version" in call_args["params"]

    @pytest.mark.asyncio
    async def test_tool_registration_triggers_notification(self, mcp_server):
        """Test that registering a tool triggers change notification."""
        # Mock WebSocket subscribers
        mock_websocket = AsyncMock()
        mcp_server.state.notification_subscribers.add(mock_websocket)

        # Create a mock tool
        from mcp.tool_registry import Tool, ToolParameter, ToolParameterType

        test_tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="param1", type=ToolParameterType.STRING, description="Test parameter"
                )
            ],
        )

        # Register tool (should trigger notification)
        await mcp_server.register_tool(test_tool)

        # Verify notification was sent
        mock_websocket.send_json.assert_called()


class TestMultiTypeResults:
    """Test multi-type tool result support."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for testing."""
        return MCP2025Server()

    @pytest.mark.asyncio
    async def test_text_content_result(self, mcp_server):
        """Test tool result with text content."""
        # Mock tool execution
        with patch.object(mcp_server.tool_registry, "execute_tool") as mock_execute:
            mock_execute.return_value = AsyncMock(
                success=True, result={"message": "Test message"}, execution_time_ms=50.0
            )

            request = JSONRPCHandler.create_request(
                id="call-1",
                method=MCPMethods.TOOLS_CALL,
                params={"name": "test_tool", "arguments": {}},
            )

            response = await mcp_server._handle_request(request)

            assert isinstance(response, JSONRPCResponse)
            result = response.result

            assert result["isError"] is False
            assert len(result["content"]) == 1
            assert result["content"][0]["type"] == "text"
            assert result["content"][0]["text"] == "Test message"

    @pytest.mark.asyncio
    async def test_image_content_result(self, mcp_server):
        """Test tool result with image content."""
        # Mock tool execution with image result
        with patch.object(mcp_server.tool_registry, "execute_tool") as mock_execute:
            mock_execute.return_value = AsyncMock(
                success=True,
                result={
                    "message": "Image generated",
                    "image": {"data": "base64-encoded-image", "mimeType": "image/png"},
                },
                execution_time_ms=150.0,
            )

            request = JSONRPCHandler.create_request(
                id="call-1",
                method=MCPMethods.TOOLS_CALL,
                params={"name": "image_tool", "arguments": {}},
            )

            response = await mcp_server._handle_request(request)

            assert isinstance(response, JSONRPCResponse)
            result = response.result

            assert result["isError"] is False
            assert len(result["content"]) == 2  # Text + Image

            # Check text content
            text_content = next(c for c in result["content"] if c["type"] == "text")
            assert text_content["text"] == "Image generated"

            # Check image content
            image_content = next(c for c in result["content"] if c["type"] == "image")
            assert image_content["data"] == "base64-encoded-image"
            assert image_content["mimeType"] == "image/png"

    @pytest.mark.asyncio
    async def test_structured_content_result(self, mcp_server):
        """Test tool result with structured content."""
        # Mock tool execution with structured data
        with patch.object(mcp_server.tool_registry, "execute_tool") as mock_execute:
            structured_data = {"temperature": 22.5, "conditions": "Partly cloudy", "humidity": 65}

            mock_execute.return_value = AsyncMock(
                success=True,
                result={"message": "Weather data retrieved", "data": structured_data},
                execution_time_ms=75.0,
            )

            request = JSONRPCHandler.create_request(
                id="call-1",
                method=MCPMethods.TOOLS_CALL,
                params={"name": "weather_tool", "arguments": {}},
            )

            response = await mcp_server._handle_request(request)

            assert isinstance(response, JSONRPCResponse)
            result = response.result

            assert result["isError"] is False
            assert "structuredContent" in result
            assert result["structuredContent"] == structured_data

    @pytest.mark.asyncio
    async def test_resource_content_result(self, mcp_server):
        """Test tool result with resource content."""
        # Mock tool execution with resource result
        with patch.object(mcp_server.tool_registry, "execute_tool") as mock_execute:
            mock_execute.return_value = AsyncMock(
                success=True,
                result={
                    "message": "Resource created",
                    "resource": {
                        "uri": "file:///tmp/test.txt",
                        "text": "Test file content",
                        "mimeType": "text/plain",
                    },
                },
                execution_time_ms=25.0,
            )

            request = JSONRPCHandler.create_request(
                id="call-1",
                method=MCPMethods.TOOLS_CALL,
                params={"name": "file_tool", "arguments": {}},
            )

            response = await mcp_server._handle_request(request)

            assert isinstance(response, JSONRPCResponse)
            result = response.result

            assert result["isError"] is False

            # Check resource content
            resource_content = next(c for c in result["content"] if c["type"] == "resource")
            assert resource_content["resource"]["uri"] == "file:///tmp/test.txt"
            assert resource_content["resource"]["text"] == "Test file content"


class TestErrorHandling:
    """Test error handling in MCP 2025 implementation."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for testing."""
        return MCP2025Server()

    @pytest.mark.asyncio
    async def test_invalid_method(self, mcp_server):
        """Test handling of invalid method."""
        request = JSONRPCHandler.create_request(id="test-1", method="invalid/method", params={})

        response = await mcp_server._handle_request(request)

        assert isinstance(response, JSONRPCErrorResponse)
        assert response.error.code == -32601  # METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_missing_params(self, mcp_server):
        """Test handling of missing required params."""
        request = JSONRPCHandler.create_request(
            id="test-1", method=MCPMethods.TOOLS_CALL, params=None
        )

        response = await mcp_server._handle_request(request)

        assert isinstance(response, JSONRPCErrorResponse)
        assert response.error.code == -32602  # INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_tool_execution_error(self, mcp_server):
        """Test handling of tool execution errors."""
        # Mock tool execution failure
        with patch.object(mcp_server.tool_registry, "execute_tool") as mock_execute:
            mock_execute.return_value = AsyncMock(
                success=False, error="Tool execution failed", execution_time_ms=10.0
            )

            request = JSONRPCHandler.create_request(
                id="call-1",
                method=MCPMethods.TOOLS_CALL,
                params={"name": "failing_tool", "arguments": {}},
            )

            response = await mcp_server._handle_request(request)

            assert isinstance(response, JSONRPCResponse)
            result = response.result

            assert result["isError"] is True
            assert "Tool execution failed" in result["content"][0]["text"]
