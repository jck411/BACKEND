#!/usr/bin/env python3
"""
Simplified MCP Self-Configuration Demo

This script demonstrates the core MCP (Model Context Protocol) functionality
without complex dependencies. Perfect for testing Phase 1 implementation.

Usage:
    python examples/simple_mcp_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MockRuntimeConfigManager:
    """Mock runtime config manager for demo purposes."""

    def __init__(self):
        self.config = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2048,
            "system_prompt": "You are a helpful AI assistant."
        }

    def get_active_provider_config(self):
        return self.config.copy()

    async def update_parameter(self, provider, model, param_name, value):
        print(f"  📝 Updated {param_name}: {self.config.get(param_name)} → {value}")
        self.config[param_name] = value
        return True


# Simple versions of the MCP classes
from mcp.parameter_schemas import ModelParameterSchemas, PopularModels


class SimpleMCPService:
    """Simplified MCP service for demo purposes."""

    def __init__(self, runtime_config_manager=None):
        self.runtime_config_manager = runtime_config_manager or MockRuntimeConfigManager()
        print("🧠 MCP Service initialized")

    async def discover_capabilities(self):
        """Discover available capabilities."""
        current_config = self.runtime_config_manager.get_active_provider_config()
        provider = current_config.get("provider", "openai")
        model = current_config.get("model", "gpt-4o-mini")

        schema = ModelParameterSchemas.get_model_schema(provider, model)

        return {
            "id": "ai_self_configuration",
            "name": "AI Self-Configuration",
            "description": "Modify AI response parameters using natural language commands",
            "current_context": {
                "provider": provider,
                "model": model,
                "supported": PopularModels.is_supported_model(provider, model),
                "current_parameters": {
                    param: {"value": current_config.get(param), "default": constraint.default}
                    for param, constraint in schema.items()
                }
            }
        }

    async def execute_natural_language_adjustment(self, natural_request):
        """Execute a natural language parameter adjustment."""
        current_config = self.runtime_config_manager.get_active_provider_config()
        provider = current_config.get("provider", "openai")
        model = current_config.get("model", "gpt-4o-mini")

        # Simple interpretation logic
        request_lower = natural_request.lower()
        adjustments = {}
        confidence = 0.5
        explanation = "Simple demo interpretation"

        # Temperature adjustments
        if any(word in request_lower for word in ["creative", "colorful", "wild"]):
            adjustments["temperature"] = min(1.2, current_config.get("temperature", 0.7) + 0.3)
            confidence = 0.85
            explanation = "Increased creativity (temperature)"

        elif any(word in request_lower for word in ["focused", "precise", "conservative"]):
            adjustments["temperature"] = max(0.1, current_config.get("temperature", 0.7) - 0.3)
            confidence = 0.85
            explanation = "Reduced randomness (temperature)"

        elif "temperature" in request_lower:
            import re
            match = re.search(r'temperature.*?(\d+\.?\d*)', request_lower)
            if match:
                adjustments["temperature"] = float(match.group(1))
                confidence = 0.95
                explanation = f"Set temperature to {adjustments['temperature']}"

        # Token adjustments
        if any(word in request_lower for word in ["longer", "detailed", "verbose"]):
            adjustments["max_tokens"] = min(4000, current_config.get("max_tokens", 2048) + 1000)
            confidence = max(confidence, 0.8)
            explanation += "; Increased response length"

        elif any(word in request_lower for word in ["shorter", "concise", "brief"]):
            adjustments["max_tokens"] = max(500, current_config.get("max_tokens", 2048) - 1000)
            confidence = max(confidence, 0.8)
            explanation += "; Reduced response length"

        # Reset
        if any(word in request_lower for word in ["reset", "default"]):
            adjustments = {"temperature": 0.7, "max_tokens": 2048}
            confidence = 0.9
            explanation = "Reset to default values"

        # Apply adjustments
        if adjustments and confidence > 0.4:
            for param, value in adjustments.items():
                await self.runtime_config_manager.update_parameter(provider, model, param, value)

            status = "applied" if confidence > 0.8 else "applied_with_explanation"
            message = f"✅ Applied changes with {confidence*100:.0f}% confidence: {explanation}"

        elif adjustments:
            status = "clarification_needed"
            message = f"🤔 Low confidence ({confidence*100:.0f}%). Could you be more specific?"

        else:
            status = "no_changes"
            message = "🤷 No clear parameter adjustments identified"

        return {
            "status": status,
            "confidence": confidence,
            "adjustments": adjustments,
            "explanation": explanation,
            "message": message
        }


async def main():
    """Run the simplified MCP demo."""

    print("🧠 Simplified MCP Self-Configuration Demo")
    print("=" * 50)

    # Initialize components
    runtime_manager = MockRuntimeConfigManager()
    mcp_service = SimpleMCPService(runtime_manager)

    # Discover capabilities
    print("\n1. 🔍 Discovering Capabilities...")
    capabilities = await mcp_service.discover_capabilities()

    print(f"Capability: {capabilities['name']}")
    print(f"Provider: {capabilities['current_context']['provider']}")
    print(f"Model: {capabilities['current_context']['model']}")
    print(f"Supported: {capabilities['current_context']['supported']}")

    print("\nCurrent Parameters:")
    for param, info in capabilities['current_context']['current_parameters'].items():
        print(f"  • {param}: {info['value']}")

    # Test requests
    test_requests = [
        "Make responses more creative and colorful",
        "Set temperature to 0.9",
        "Make responses shorter and more concise",
        "Reduce randomness and be more focused",
        "This is vague",
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

        if result.get('adjustments'):
            print("Adjustments:", result['adjustments'])

        await asyncio.sleep(0.3)  # Small delay for readability

    # Final state
    print(f"\n3. 📊 Final Configuration")
    print("=" * 50)
    final_config = runtime_manager.get_active_provider_config()
    for param, value in final_config.items():
        print(f"  • {param}: {value}")

    print(f"\n✅ Simplified MCP Demo Complete!")


if __name__ == "__main__":
    asyncio.run(main())
