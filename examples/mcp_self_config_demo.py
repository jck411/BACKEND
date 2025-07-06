#!/usr/bin/env python3
"""
MCP Self-Configuration Demo

This script demonstrates the MCP (Model Context Protocol) self-configuration
capabilities. It shows how an AI can modify its own parameters through
natural language commands.

Phase 1 Implementation:
- Natural language parameter interpretation
- Confidence-based decision making
- Integration with runtime configuration
- Support for popular models (OpenAI, Anthropic, Gemini, OpenRouter)

Usage:
    python examples/mcp_self_config_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.self_config_service import MCPSelfConfigService
from common.runtime_config import get_runtime_config_manager
from common.logging import setup_logging, get_logger
from common.config import Config

# Fix relative import issue by importing the actual dependencies
import structlog


async def main():
    """Demonstrate MCP self-configuration capabilities."""

    # Setup logging
    config = Config()
    setup_logging(config)
    logger = get_logger(__name__)

    print("🧠 MCP Self-Configuration Demo")
    print("=" * 50)

    # Initialize MCP service
    runtime_config_manager = get_runtime_config_manager()
    mcp_service = MCPSelfConfigService(runtime_config_manager)

    # Discover capabilities
    print("\n1. 🔍 Discovering MCP Capabilities...")
    capabilities = await mcp_service.discover_capabilities()

    print(f"Capability: {capabilities['name']}")
    print(f"Description: {capabilities['description']}")
    print(f"Current Provider: {capabilities['current_context']['provider']}")
    print(f"Current Model: {capabilities['current_context']['model']}")
    print(f"Supported: {capabilities['current_context']['supported']}")

    print("\nCurrent Parameters:")
    for param, info in capabilities['current_context']['current_parameters'].items():
        status = "(default)" if info['is_default'] else "(custom)"
        print(f"  • {param}: {info['value']} {status}")

    # Test natural language adjustments
    test_requests = [
        "Make responses more creative and colorful",
        "Set temperature to 0.9",
        "Make responses shorter and more concise",
        "Reduce randomness and be more focused",
        "Turn up creativity to maximum",
        "This is a vague request that should trigger clarification",
        "Reset to default settings"
    ]

    print(f"\n2. 🎛️  Testing Natural Language Adjustments...")
    print("=" * 50)

    for i, request in enumerate(test_requests, 1):
        print(f"\n{i}. Testing: '{request}'")
        print("-" * 40)

        result = await mcp_service.execute_natural_language_adjustment(request)

        print(f"Status: {result['status']}")
        print(f"Confidence: {result['confidence']:.1%}")
        print(f"Message: {result['message']}")

        if result['status'] == 'applied' or result['status'] == 'applied_with_explanation':
            print("Applied adjustments:")
            for param, value in result['adjustments'].items():
                print(f"  • {param}: {value}")

        elif result['status'] == 'clarification_needed':
            print("Clarification request:")
            print(result['clarification_request'])

        # Small delay for readability
        await asyncio.sleep(0.5)

    # Show final configuration
    print(f"\n3. 📊 Final Configuration")
    print("=" * 50)

    final_capabilities = await mcp_service.discover_capabilities()
    print("\nFinal Parameters:")
    for param, info in final_capabilities['current_context']['current_parameters'].items():
        status = "(default)" if info['is_default'] else "(modified)"
        print(f"  • {param}: {info['value']} {status}")

    print(f"\n✅ MCP Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("• Natural language parameter interpretation")
    print("• Confidence-based decision making")
    print("• Real-time configuration updates")
    print("• Provider-aware parameter validation")
    print("• Clarification requests for ambiguous input")


if __name__ == "__main__":
    asyncio.run(main())
