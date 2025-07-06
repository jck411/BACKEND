#!/usr/bin/env python3
"""
Example of switching between different AI providers using runtime configuration.
Following PROJECT_RULES.md for async operations and testing.

This demonstrates:
1. Runtime configuration management
2. Strict mode (no fallbacks)
3. Provider switching via configuration file
4. Future-ready for frontend integration
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.config import load_config
from common.runtime_config import get_runtime_config_manager, update_active_provider
from router.request_router import RequestRouter


async def test_runtime_configuration():
    """Test runtime configuration management."""
    print("🔧 Testing Runtime Configuration")
    print("=" * 50)

    # Get runtime config manager
    runtime_manager = get_runtime_config_manager()

    # Show current configuration
    current_config = runtime_manager.get_active_provider_config()
    print("📋 Current Configuration:")
    print(f"   Provider: {current_config['provider']}")
    print(f"   Model: {current_config['model']}")
    print(f"   Temperature: {current_config['temperature']}")
    print(f"   Strict Mode: {runtime_manager.is_strict_mode()}")


async def test_provider_switching():
    """Test switching between different providers."""
    print("\n🔄 Testing Provider Switching (Strict Mode)")
    print("=" * 50)

    config = load_config()
    providers_to_test = ["openai", "anthropic", "gemini", "openrouter"]

    for provider in providers_to_test:
        print(f"\n🧪 Switching to {provider}...")

        # Update provider via runtime config
        success = update_active_provider(provider)
        if not success:
            print(f"   ❌ Failed to switch to {provider}")
            continue

        try:
            # Create new router to pick up config changes
            router = RequestRouter(config)

            # Get the active adapter (this will use strict mode)
            active_adapter = router._get_active_adapter()

            # Find which adapter was actually selected
            selected_provider = None
            for name, adapter in router.adapters.items():
                if adapter is active_adapter:
                    selected_provider = name
                    break

            if selected_provider == provider:
                print(f"   ✅ {provider} successfully selected")
            else:
                print(f"   ⚠️  Expected {provider}, got {selected_provider}")

            # Test health check
            health = await active_adapter.health_check()
            status = "🟢 healthy" if health else "🔴 unhealthy"
            print(f"   Health check: {status}")

        except ValueError as e:
            print(f"   ❌ Provider not available: {e}")
        except Exception as e:
            print(f"   ❌ Error with {provider}: {e}")


async def demo_configuration_examples():
    """Show examples of different configuration patterns."""
    print("\n📝 Configuration Examples")
    print("=" * 50)

    examples = [
        {
            "name": "OpenAI Primary (Strict Mode)",
            "provider": "openai",
            "use_case": "Fastest responses, most reliable"
        },
        {
            "name": "Anthropic Primary (Strict Mode)",
            "provider": "anthropic",
            "use_case": "Best reasoning, ethical responses"
        },
        {
            "name": "Multi-Model via OpenRouter (Strict Mode)",
            "provider": "openrouter",
            "use_case": "Access to 100+ models"
        },
        {
            "name": "Gemini Primary (Strict Mode)",
            "provider": "gemini",
            "use_case": "Google's latest multimodal AI"
        },
    ]

    for example in examples:
        print(f"\n📋 {example['name']}:")
        print(f"   Provider: {example['provider']}")
        print(f"   Use Case: {example['use_case']}")
        print("   Configuration:")
        print("     runtime_config.yaml:")
        print("       provider:")
        print(f"         active: \"{example['provider']}\"")
        print("       runtime:")
        print("         strict_mode: true")


async def show_environment_setup():
    """Show how to set up environment variables."""
    print("\n🔧 Environment Setup")
    print("=" * 50)

    print("Environment variables (API keys only):")
    print()
    print("# OpenAI")
    print("export OPENAI_API_KEY=sk-...")
    print()
    print("# Anthropic Claude")
    print("export ANTHROPIC_API_KEY=sk-ant-...")
    print()
    print("# Google Gemini")
    print("export GEMINI_API_KEY=AIza...")
    print()
    print("# OpenRouter (access to 100+ models)")
    print("export OPENROUTER_API_KEY=sk-or-...")
    print()
    print("Configuration files:")
    print("• runtime_config.yaml - Provider selection and model settings")
    print("• config.yaml - System configuration (gateway, router, etc.)")


async def demo_runtime_switching():
    """Demonstrate runtime provider switching."""
    print("\n⚡ Runtime Provider Switching Demo")
    print("=" * 50)

    print("This shows how to switch providers at runtime:")
    print()
    print("1. Via Python API:")
    print("   from common.runtime_config import update_active_provider")
    print("   update_active_provider('anthropic')")
    print()
    print("2. Via editing runtime_config.yaml:")
    print("   provider:")
    print("     active: 'anthropic'")
    print()
    print("3. Future: Via frontend API call:")
    print("   POST /api/config/provider")
    print("   {\"provider\": \"anthropic\"}")
    print()
    print("✨ Changes take effect immediately (strict mode - no fallbacks)")


async def main():
    """Main demonstration function."""
    print("🚀 Multi-Provider Runtime Configuration Demo")
    print("=" * 50)

    await test_runtime_configuration()
    await test_provider_switching()
    await demo_configuration_examples()
    await show_environment_setup()
    await demo_runtime_switching()

    print("\n" + "=" * 50)
    print("✨ Runtime configuration system is ready!")
    print()
    print("Key features:")
    print("✅ Strict mode - no fallbacks, fail fast")
    print("✅ Runtime provider switching via config file")
    print("✅ Environment variables only for API keys")
    print("✅ Automatic configuration reloading")
    print("✅ Future-ready for frontend integration")
    print()
    print("Files created:")
    print("📄 runtime_config.yaml - Runtime configuration")
    print("📄 config.yaml - System configuration")
    print()
    print("Next steps:")
    print("1. Set your API keys in environment variables")
    print("2. Edit runtime_config.yaml to select your provider")
    print("3. Start the server: uvicorn src.main:app --reload")
    print("4. Provider switches take effect immediately!")


if __name__ == "__main__":
    asyncio.run(main())
