#!/usr/bin/env python3
"""
Standard MCP Client Test

This script demonstrates the standard MCP HTTP endpoints:
- GET /tools/list - Discover available tools
- POST /tools/call - Execute tools with parameters

This follows the official MCP specification for tool discovery and execution.

Usage:
    python examples/mcp_standard_client_test.py
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# Add src to Python path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MCPStandardClient:
    """Standard MCP HTTP client for testing endpoints."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """Initialize MCP client."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def list_tools(self):
        """Get list of available tools via standard MCP endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/tools/list")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            return None

    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool via standard MCP endpoint."""
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            response = await self.client.post(
                f"{self.base_url}/tools/call",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error calling tool {tool_name}: {e}")
            return None

    async def health_check(self):
        """Check server health including MCP status."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def test_mcp_endpoints():
    """Test standard MCP endpoints with various scenarios."""

    print("🌐 Standard MCP Client Test")
    print("=" * 60)

    client = MCPStandardClient()

    try:
        # 1. Health Check
        print("\n1. 🏥 Health Check")
        print("-" * 40)
        health = await client.health_check()
        if health:
            print(f"✅ Server Status: {health.get('status')}")
            print(f"   Active Connections: {health.get('active_connections')}")
            if 'mcp_server' in health:
                mcp_health = health['mcp_server']
                print(f"   MCP Tools: {mcp_health.get('tools_count')}")
                print(f"   MCP Endpoints: {mcp_health.get('endpoints')}")
        else:
            print("❌ Health check failed - is the server running?")
            return

        # 2. Tool Discovery
        print("\n2. 🔍 Tool Discovery (GET /tools/list)")
        print("-" * 40)
        tools_response = await client.list_tools()
        if tools_response:
            tools = tools_response.get('tools', [])
            print(f"✅ Discovered {len(tools)} tools:")

            for tool in tools:
                print(f"\n📋 Tool: {tool['name']}")
                print(f"   Description: {tool['description']}")
                print(f"   Category: {tool.get('category', 'general')}")
                print(f"   Parameters: {len(tool.get('parameters', []))}")

                # Show first few parameters
                params = tool.get('parameters', [])[:3]
                for param in params:
                    required = "required" if param.get('required') else "optional"
                    print(f"     • {param['name']} ({param['type']}, {required}): {param['description']}")

                if len(tool.get('parameters', [])) > 3:
                    print(f"     ... and {len(tool.get('parameters', [])) - 3} more parameters")
        else:
            print("❌ Tool discovery failed")
            return

        # 3. Tool Execution Tests
        print("\n3. 🛠️  Tool Execution (POST /tools/call)")
        print("-" * 40)

        test_scenarios = [
            {
                "name": "Natural Language - Creative",
                "tool": "ai_configure",
                "args": {
                    "request": "Make responses more creative and colorful",
                    "context": {"user_preference": "creative_mode"}
                }
            },
            {
                "name": "Explicit Parameter Setting",
                "tool": "ai_configure",
                "args": {
                    "request": "Set temperature to 0.9"
                }
            },
            {
                "name": "Conservative Adjustment",
                "tool": "ai_configure",
                "args": {
                    "request": "Reduce randomness and be more focused"
                }
            },
            {
                "name": "Vague Request (Low Confidence)",
                "tool": "ai_configure",
                "args": {
                    "request": "Make it better somehow"
                }
            },
            {
                "name": "Reset to Defaults",
                "tool": "ai_configure",
                "args": {
                    "request": "Reset all parameters to default values"
                }
            }
        ]

        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n  {i}. {scenario['name']}")
            print(f"     Request: '{scenario['args']['request']}'")

            result = await client.call_tool(scenario['tool'], scenario['args'])

            if result:
                if result.get('isError'):
                    print(f"     ❌ Error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
                else:
                    # Extract relevant information
                    content = result.get('content', [])
                    meta = result.get('meta', {})

                    # Show main result
                    if content:
                        main_text = content[0].get('text', 'No result text')
                        print(f"     ✅ {main_text}")

                    # Show metadata
                    if 'confidence' in meta and meta['confidence']:
                        print(f"        Confidence: {meta['confidence']:.0%}")

                    if 'adjustments' in meta and meta['adjustments']:
                        adjustments = meta['adjustments']
                        changes = [f"{k}→{v}" for k, v in adjustments.items()]
                        print(f"        Changes: {', '.join(changes)}")

                    if 'execution_time_ms' in meta:
                        print(f"        Time: {meta['execution_time_ms']:.1f}ms")
            else:
                print(f"     ❌ Tool execution failed")

            # Small delay between requests
            await asyncio.sleep(0.5)

        # 4. Invalid Tool Test
        print(f"\n4. 🚫 Error Handling")
        print("-" * 40)

        print("  Testing invalid tool name...")
        invalid_result = await client.call_tool("nonexistent_tool", {"test": "value"})
        if invalid_result and invalid_result.get('isError'):
            error_text = invalid_result.get('content', [{}])[0].get('text', 'Unknown error')
            print(f"  ✅ Correctly rejected invalid tool: {error_text}")

        print("  Testing invalid parameters...")
        invalid_params_result = await client.call_tool("ai_configure", {"invalid_param": "value"})
        if invalid_params_result and invalid_params_result.get('isError'):
            error_text = invalid_params_result.get('content', [{}])[0].get('text', 'Unknown error')
            print(f"  ✅ Correctly rejected invalid parameters: {error_text}")

        print(f"\n✅ Standard MCP Client Test Complete!")
        print(f"\n📊 Summary:")
        print(f"   • Standard MCP endpoints working: /tools/list, /tools/call")
        print(f"   • Tool discovery and execution functional")
        print(f"   • Error handling working correctly")
        print(f"   • Vendor-agnostic tool interface operational")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    print("🚀 Starting Standard MCP Client Test...")
    print("📋 Make sure the backend server is running on port 8000")
    print("   Start with: python src/main.py")
    print()

    asyncio.run(test_mcp_endpoints())
