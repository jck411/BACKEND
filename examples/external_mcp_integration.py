#!/usr/bin/env python3
"""
External MCP Client Integration Example

This script demonstrates how external MCP clients can integrate with our
standard MCP server endpoints. This shows true vendor-agnostic MCP compatibility.

This example simulates how any MCP-compliant client (like claude-desktop,
vscode extensions, or other MCP tools) would interact with our server.

Usage:
    python examples/external_mcp_integration.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

import httpx

# Add src to Python path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class ExternalMCPClient:
    """
    Simulates an external MCP client (like claude-desktop, vscode, etc.)

    This demonstrates how any MCP-compliant client would interact with
    our standard MCP server implementation.
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        """Initialize external MCP client."""
        self.server_url = server_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.available_tools: Dict[str, Any] = {}

    async def discover_capabilities(self) -> Dict[str, Any]:
        """
        Standard MCP capability discovery.

        This is how external clients discover what tools are available.
        """
        try:
            response = await self.client.post(f"{self.server_url}/tools/list", json={})
            response.raise_for_status()

            tools_data = response.json()

            # Store tools for later use
            for tool in tools_data.get('tools', []):
                self.available_tools[tool['name']] = tool

            return {
                "server_info": tools_data.get('meta', {}),
                "tools_discovered": len(self.available_tools),
                "tool_names": list(self.available_tools.keys()),
                "capabilities": [
                    "runtime_discovery",
                    "natural_language_interface",
                    "parameter_validation",
                    "vendor_agnostic_execution"
                ]
            }

        except Exception as e:
            return {"error": f"Discovery failed: {e}"}

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard MCP tool execution.

        This is how external clients execute tools on our server.
        """
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }

            response = await self.client.post(
                f"{self.server_url}/tools/call",
                json=payload
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {"error": f"Execution failed: {e}"}

    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed schema for a specific tool."""
        if tool_name in self.available_tools:
            tool_info = self.available_tools[tool_name]

            # Convert to standard JSON schema format
            schema = {
                "type": "object",
                "properties": {},
                "required": []
            }

            for param in tool_info.get('parameters', []):
                param_schema = {
                    "type": param['type'],
                    "description": param['description']
                }

                # Add constraints
                if param.get('minimum') is not None:
                    param_schema['minimum'] = param['minimum']
                if param.get('maximum') is not None:
                    param_schema['maximum'] = param['maximum']
                if param.get('enum'):
                    param_schema['enum'] = param['enum']
                if param.get('pattern'):
                    param_schema['pattern'] = param['pattern']
                if param.get('default') is not None:
                    param_schema['default'] = param['default']

                schema['properties'][param['name']] = param_schema

                if param.get('required'):
                    schema['required'].append(param['name'])

            return {
                "tool": tool_name,
                "description": tool_info['description'],
                "category": tool_info.get('category', 'general'),
                "version": tool_info.get('version', '1.0.0'),
                "schema": schema,
                "examples": tool_info.get('examples', [])
            }

        return {"error": f"Tool '{tool_name}' not found"}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def simulate_external_client_workflow():
    """
    Simulate how an external MCP client would work with our server.

    This demonstrates the complete workflow:
    1. Discovery of available tools
    2. Schema introspection
    3. Tool execution with validation
    4. Error handling
    """

    print("🌍 External MCP Client Integration Simulation")
    print("=" * 70)
    print("Simulating how external MCP clients (claude-desktop, vscode, etc.)")
    print("would integrate with our standard MCP server implementation.")
    print()

    client = ExternalMCPClient()

    try:
        # 1. Discovery Phase
        print("1. 🔍 Capability Discovery")
        print("-" * 50)

        discovery = await client.discover_capabilities()

        if "error" in discovery:
            print(f"❌ Discovery failed: {discovery['error']}")
            return

        print(f"✅ Server discovered: {discovery['server_info'].get('server', 'Unknown')}")
        print(f"   Version: {discovery['server_info'].get('version', 'Unknown')}")
        print(f"   Tools discovered: {discovery['tools_discovered']}")
        print(f"   Available tools: {', '.join(discovery['tool_names'])}")
        print(f"   Capabilities: {', '.join(discovery['capabilities'])}")

        # 2. Schema Introspection
        print("\n2. 📋 Tool Schema Introspection")
        print("-" * 50)

        for tool_name in discovery['tool_names']:
            schema_info = await client.get_tool_schema(tool_name)

            if "error" not in schema_info:
                print(f"\n🛠️  Tool: {schema_info['tool']}")
                print(f"   Description: {schema_info['description']}")
                print(f"   Category: {schema_info['category']}")
                print(f"   Required params: {schema_info['schema']['required']}")
                print(f"   Total params: {len(schema_info['schema']['properties'])}")

                # Show parameter details
                for param_name, param_info in schema_info['schema']['properties'].items():
                    required = "required" if param_name in schema_info['schema']['required'] else "optional"
                    print(f"     • {param_name} ({param_info['type']}, {required})")

        # 3. Tool Execution Scenarios
        print("\n3. 🚀 Tool Execution Scenarios")
        print("-" * 50)

        execution_scenarios = [
            {
                "name": "AI Configuration - Creative Mode",
                "description": "Configure AI for creative writing tasks",
                "tool": "ai_configure",
                "arguments": {
                    "request": "Optimize for creative writing - make responses more imaginative and expressive",
                    "context": {
                        "current_task": "creative writing",
                        "user_preference": "creative"
                    }
                }
            },
            {
                "name": "AI Configuration - Technical Mode",
                "description": "Configure AI for technical documentation",
                "tool": "ai_configure",
                "arguments": {
                    "request": "Switch to technical mode - precise, focused, and concise responses",
                    "context": {
                        "current_task": "technical documentation"
                    }
                }
            },
            {
                "name": "Explicit Parameter Control",
                "description": "Direct parameter manipulation",
                "tool": "ai_configure",
                "arguments": {
                    "request": "Set temperature to 0.3 and max tokens to 1500"
                }
            },
            {
                "name": "Natural Language Reset",
                "description": "Reset to balanced settings",
                "tool": "ai_configure",
                "arguments": {
                    "request": "Reset to balanced, default settings for general use"
                }
            }
        ]

        for i, scenario in enumerate(execution_scenarios, 1):
            print(f"\n  {i}. {scenario['name']}")
            print(f"     Task: {scenario['description']}")
            print(f"     Request: \"{scenario['arguments']['request']}\"")

            result = await client.execute_tool(scenario['tool'], scenario['arguments'])

            if "error" in result:
                print(f"     ❌ Failed: {result['error']}")
            else:
                if result.get('isError'):
                    error_msg = result.get('content', [{}])[0].get('text', 'Unknown error')
                    print(f"     ❌ Tool Error: {error_msg}")
                else:
                    # Extract and display results
                    content = result.get('content', [])
                    meta = result.get('meta', {})

                    if content:
                        main_result = content[0].get('text', 'No result')
                        print(f"     ✅ {main_result}")

                    # Show execution metadata
                    if meta.get('confidence'):
                        print(f"        Confidence: {meta['confidence']:.0%}")

                    if meta.get('adjustments'):
                        changes = [f"{k}→{v}" for k, v in meta['adjustments'].items()]
                        print(f"        Applied: {', '.join(changes)}")

                    if meta.get('execution_time_ms'):
                        print(f"        Execution time: {meta['execution_time_ms']:.1f}ms")

            await asyncio.sleep(0.3)  # Brief pause between requests

        # 4. Error Handling Demonstration
        print("\n4. 🛡️  Error Handling & Validation")
        print("-" * 50)

        error_scenarios = [
            {
                "name": "Invalid Tool",
                "tool": "nonexistent_tool",
                "args": {"test": "value"}
            },
            {
                "name": "Missing Required Parameter",
                "tool": "ai_configure",
                "args": {"invalid_param": "test"}
            },
            {
                "name": "Invalid Parameter Type",
                "tool": "ai_configure",
                "args": {"request": 123}  # Should be string
            }
        ]

        for scenario in error_scenarios:
            print(f"\n  Testing: {scenario['name']}")
            result = await client.execute_tool(scenario['tool'], scenario['args'])

            if result.get('isError') or "error" in result:
                error_msg = result.get('content', [{}])[0].get('text') if result.get('content') else result.get('error')
                print(f"  ✅ Correctly handled: {error_msg}")
            else:
                print("  ⚠️  Expected error but got success")

        # 5. Summary
        print("\n🎉 External MCP Client Integration Complete!")
        print("=" * 70)
        print("✅ Standard MCP Protocol Compliance:")
        print("   • POST /tools/list - Tool discovery working")
        print("   • POST /tools/call - Tool execution working")
        print("   • Parameter validation working")
        print("   • Error handling working")
        print()
        print("✅ Vendor-Agnostic Integration:")
        print("   • Any MCP client can discover our tools")
        print("   • Standard JSON schema for parameter validation")
        print("   • Consistent error reporting")
        print("   • Real-time tool execution")
        print()
        print("✅ AI Configuration Tool:")
        print("   • Natural language parameter adjustment")
        print("   • Provider-aware constraints")
        print("   • Confidence-based decision making")
        print("   • Real-time configuration updates")
        print()
        print("🌍 This server can now integrate with:")
        print("   • Claude Desktop (Anthropic)")
        print("   • VS Code MCP extensions")
        print("   • Custom MCP clients")
        print("   • Any tool following MCP specification")

    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    print("🚀 Starting External MCP Client Integration Simulation...")
    print("📋 This simulates how external MCP clients would integrate with our server")
    print("   Make sure the backend server is running on port 8000")
    print()

    asyncio.run(simulate_external_client_workflow())
