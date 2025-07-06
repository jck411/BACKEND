#!/usr/bin/env python3
"""
Provider switching utility for easy runtime configuration.

Usage:
  python switch_provider.py openai
  python switch_provider.py anthropic
  python switch_provider.py gemini
  python switch_provider.py openrouter
  python switch_provider.py --show    # Show current provider
  python switch_provider.py --list    # List available providers
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from common.runtime_config import get_runtime_config_manager, update_active_provider


def show_current_provider():
    """Show the currently active provider."""
    runtime_manager = get_runtime_config_manager()
    config = runtime_manager.get_active_provider_config()

    print("🔍 Current Provider Configuration:")
    print(f"   Provider: {config['provider']}")
    print(f"   Model: {config['model']}")
    print(f"   Temperature: {config['temperature']}")
    print(f"   Max Tokens: {config['max_tokens']}")
    print(f"   Strict Mode: {runtime_manager.is_strict_mode()}")


def list_available_providers():
    """List all available providers."""
    runtime_manager = get_runtime_config_manager()
    config = runtime_manager.load_runtime_config()

    providers = config.get("provider", {}).get("models", {}).keys()

    print("📋 Available Providers:")
    for provider in providers:
        print(f"   • {provider}")


def switch_provider(provider: str):
    """Switch to the specified provider."""
    print(f"🔄 Switching to {provider}...")

    success = update_active_provider(provider)

    if success:
        print(f"✅ Successfully switched to {provider}")
        show_current_provider()
    else:
        print(f"❌ Failed to switch to {provider}")
        print("   Check that the provider is configured in runtime_config.yaml")


def main():
    """Main CLI function."""
    if len(sys.argv) < 2:
        print("🚀 Provider Switching Utility")
        print("=" * 40)
        print()
        print("Usage:")
        print("  python switch_provider.py <provider>")
        print("  python switch_provider.py --show")
        print("  python switch_provider.py --list")
        print()
        print("Examples:")
        print("  python switch_provider.py openai")
        print("  python switch_provider.py anthropic")
        print("  python switch_provider.py gemini")
        print("  python switch_provider.py openrouter")
        return

    command = sys.argv[1].lower()

    if command == "--show":
        show_current_provider()
    elif command == "--list":
        list_available_providers()
    elif command in ["openai", "anthropic", "gemini", "openrouter"]:
        switch_provider(command)
    else:
        print(f"❌ Unknown provider or command: {command}")
        print("Available providers: openai, anthropic, gemini, openrouter")
        print("Available commands: --show, --list")


if __name__ == "__main__":
    main()
