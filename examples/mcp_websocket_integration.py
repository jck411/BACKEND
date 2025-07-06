#!/usr/bin/env python3
"""
MCP WebSocket Integration Example

This script demonstrates how the MCP service integrates with the WebSocket
router system for real-time AI self-configuration.

This shows the complete flow:
1. WebSocket receives MCP_REQUEST message
2. Router processes through MCP manager
3. Self-configuration service interprets natural language
4. Parameters are updated in runtime config
5. Response is streamed back via WebSocket

Usage:
    python examples/mcp_websocket_integration.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from router.message_types import RequestType, RouterRequest
from common.models import WebSocketResponse, Chunk, ChunkType


class MockWebSocketConnection:
    """Mock WebSocket connection for demo purposes."""

    def __init__(self, connection_id="demo-001"):
        self.connection_id = connection_id
        self.messages = []

    async def send_json(self, data):
        """Simulate sending JSON over WebSocket."""
        self.messages.append(data)
        print(f"📤 WebSocket Send: {json.dumps(data, indent=2)}")


class MockRouter:
    """Mock router with MCP integration for demo."""

    def __init__(self):
        # Import MCP components
        from mcp.connection_manager import MCPConnectionManager
        from common.runtime_config import get_runtime_config_manager

        self.runtime_config_manager = get_runtime_config_manager()
        self.mcp_manager = MCPConnectionManager(self.runtime_config_manager)
        print("🔧 Mock Router initialized with MCP support")

    async def process_request(self, router_request):
        """Process router request and yield responses."""

        if router_request.request_type == RequestType.MCP_REQUEST:
            print(f"🧠 Processing MCP request...")

            # Handle MCP request through the MCP manager
            mcp_response = await self.mcp_manager.handle_mcp_request(router_request.payload)

            # Yield MCP response
            yield WebSocketResponse(
                request_id=router_request.request_id,
                status="chunk",
                chunk=Chunk(
                    type=ChunkType.METADATA,
                    data=str(mcp_response.get("result", mcp_response)),
                    metadata={
                        "source": "mcp_service",
                        "mcp_status": mcp_response.get("status", "unknown"),
                        "mcp_type": mcp_response.get("type"),
                        "capability_id": mcp_response.get("capability_id")
                    }
                )
            )

            # Yield completion
            yield WebSocketResponse(
                request_id=router_request.request_id,
                status="complete"
            )

        else:
            yield WebSocketResponse(
                request_id=router_request.request_id,
                status="error",
                error=f"Unsupported request type: {router_request.request_type}"
            )


async def simulate_mcp_request(websocket, router, request_data):
    """Simulate a complete MCP request flow."""

    # Create router request
    router_request = RouterRequest(
        request_id=request_data["request_id"],
        request_type=RequestType.MCP_REQUEST,
        payload=request_data["payload"],
        connection_id=websocket.connection_id
    )

    print(f"📨 Processing Request: {request_data['description']}")
    print(f"   Payload: {router_request.payload}")

    # Process through router
    async for response in router.process_request(router_request):
        # Send response via WebSocket
        response_data = {
            "request_id": response.request_id,
            "status": response.status,
            "type": "mcp_response"
        }

        if hasattr(response, 'chunk') and response.chunk:
            response_data["chunk"] = {
                "type": response.chunk.type.value if hasattr(response.chunk.type, 'value') else str(response.chunk.type),
                "data": response.chunk.data,
                "metadata": response.chunk.metadata
            }

        if hasattr(response, 'error') and response.error:
            response_data["error"] = response.error

        await websocket.send_json(response_data)

    print("")


async def main():
    """Demonstrate MCP WebSocket integration."""

    print("🌐 MCP WebSocket Integration Demo")
    print("=" * 60)

    # Initialize components
    websocket = MockWebSocketConnection()
    router = MockRouter()

    # Test scenarios
    test_scenarios = [
        {
            "description": "Discover all MCP capabilities",
            "request_id": "req-001",
            "payload": {
                "action": "discover_all"
            }
        },
        {
            "description": "Natural language adjustment - more creative",
            "request_id": "req-002",
            "payload": {
                "action": "execute",
                "capability_id": "ai_self_configuration",
                "parameters": {
                    "request": "Make responses more creative and colorful",
                    "context": {"user_preference": "creative_mode"}
                }
            }
        },
        {
            "description": "Explicit parameter setting",
            "request_id": "req-003",
            "payload": {
                "action": "execute",
                "capability_id": "ai_self_configuration",
                "parameters": {
                    "request": "Set temperature to 0.8"
                }
            }
        },
        {
            "description": "Vague request requiring clarification",
            "request_id": "req-004",
            "payload": {
                "action": "execute",
                "capability_id": "ai_self_configuration",
                "parameters": {
                    "request": "Make it better somehow"
                }
            }
        },
        {
            "description": "Reset to defaults",
            "request_id": "req-005",
            "payload": {
                "action": "execute",
                "capability_id": "ai_self_configuration",
                "parameters": {
                    "request": "Reset all parameters to default values"
                }
            }
        }
    ]

    # Execute test scenarios
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['description']}")
        print("-" * 60)
        await simulate_mcp_request(websocket, router, scenario)
        await asyncio.sleep(0.5)  # Small delay between requests

    print(f"✅ MCP WebSocket Integration Demo Complete!")
    print(f"\n📊 Summary:")
    print(f"   • Total requests processed: {len(test_scenarios)}")
    print(f"   • WebSocket messages sent: {len(websocket.messages)}")
    print(f"   • Integration: Router ↔ MCP ↔ WebSocket ✅")

    # Show current configuration state
    final_config = router.runtime_config_manager.get_active_provider_config()
    print(f"\n🎛️  Final Configuration:")
    for param, value in final_config.items():
        print(f"   • {param}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
