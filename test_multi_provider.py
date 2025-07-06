#!/usr/bin/env python3
"""
Test script for multi-provider functionality.
Following PROJECT_RULES.md for testing and async operations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from common.config import load_config
from common.runtime_config import get_runtime_config_manager
from router.request_router import RequestRouter


async def test_multi_provider_setup():
    """Test that multi-provider setup works correctly."""
    print("🧪 Testing Multi-Provider Setup")
    print("=" * 50)

    # Load configuration
    config = load_config()
    print("✅ Configuration loaded")
    print(f"   Active provider: {config.providers.active}")
    print(f"   Strict mode: {config.providers.strict_mode}")

    # Show runtime configuration
    runtime_manager = get_runtime_config_manager()
    runtime_config = runtime_manager.get_active_provider_config()
    print(f"   Runtime provider: {runtime_config['provider']}")
    print(f"   Runtime model: {runtime_config['model']}")

    # Initialize router
    try:
        router = RequestRouter(config)
        print("✅ Router initialized")
        print(f"   Available adapters: {list(router.adapters.keys())}")

        # Test health checks
        health_status = await router.health_check_all_providers()
        print("✅ Health check completed")
        for provider, healthy in health_status.items():
            status = "🟢 healthy" if healthy else "🔴 unhealthy"
            print(f"   {provider}: {status}")

        print("\n🎉 Multi-provider setup test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during router initialization: {e}")
        return False


async def test_strict_mode():
    """Test strict mode behavior (no fallbacks)."""
    print("\n� Testing Strict Mode (No Fallbacks)")
    print("=" * 50)

    config = load_config()

    # Test with invalid active provider - should fail in strict mode
    runtime_manager = get_runtime_config_manager()

    # Save current provider
    original_config = runtime_manager.get_active_provider_config()
    original_provider = original_config['provider']

    try:
        # Try to switch to invalid provider
        print("   Testing invalid provider (should fail)...")
        success = runtime_manager.update_active_provider("invalid_provider")

        if not success:
            print("✅ Strict mode works - invalid provider rejected")
            return True
        else:
            # This shouldn't happen, but if it does, test router behavior
            router = RequestRouter(config)
            try:
                router._get_active_adapter()  # This should fail in strict mode
                print("❌ Strict mode failed - invalid provider was accepted")
                return False
            except ValueError as e:
                print("✅ Strict mode works - router rejected invalid provider")
                print(f"   Error: {e}")
                return True
    except Exception as e:
        print(f"❌ Strict mode test failed: {e}")
        return False
    finally:
        # Restore original provider
        runtime_manager.update_active_provider(original_provider)


async def main():
    """Main test function."""
    print("🚀 Multi-Provider Backend Test Suite")
    print("=" * 50)

    # Check environment variables
    providers_available = []
    if os.getenv("OPENAI_API_KEY"):
        providers_available.append("OpenAI")
    if os.getenv("ANTHROPIC_API_KEY"):
        providers_available.append("Anthropic")
    if os.getenv("GEMINI_API_KEY"):
        providers_available.append("Gemini")
    if os.getenv("OPENROUTER_API_KEY"):
        providers_available.append("OpenRouter")

    print("📋 Environment check:")
    if providers_available:
        print(f"   Available providers: {', '.join(providers_available)}")
    else:
        print("   ⚠️  No API keys found in environment")
        print("   To test with real providers, set:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - GEMINI_API_KEY")
        print("   - OPENROUTER_API_KEY")

    print()

    # Run tests
    test_results = []
    test_results.append(await test_multi_provider_setup())
    test_results.append(await test_strict_mode())

    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    passed = sum(test_results)
    total = len(test_results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        return 0
    else:
        print(f"❌ Some tests failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
