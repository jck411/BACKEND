
# Backend Project

> Multi-provider AI streaming platform with runtime configuration and WebSocket connectivity. Supports OpenAI, Anthropic, Gemini, and OpenRouter with immediate provider switching without restart. See [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) for full architecture, features, and implementation details.

## Current Status
✅ **Working WebSocket Gateway** with request routing, connection management, and structured logging
✅ **Multi-Provider AI Integration** with OpenAI, Anthropic, Gemini, and OpenRouter adapters
✅ **Runtime Configuration System** with automatic reloading and provider switching
✅ **Strict Mode** - No fallbacks, fail fast behavior following project rules
✅ **Phase 1 MCP Implementation** - AI self-configuration via natural language complete
🔄 **Planned**: Advanced MCP features, home automation, aggregation features

## Quick Start

### 1. Setup Environment
```bash
# Install dependencies
uv sync --strict

# Copy environment template (API keys only)
cp .env.example .env

# Add your API keys to .env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
OPENROUTER_API_KEY=your_openrouter_key
```

### 2. Start Server
```bash
# Start server
uv run python src/main.py

# Or use script
./scripts/start_dev.sh
```

### 3. Switch AI Providers (Runtime)
```bash
# View current configuration
uv run python switch_provider.py show

# Switch to different provider
uv run python switch_provider.py switch openai
uv run python switch_provider.py switch anthropic
uv run python switch_provider.py switch gemini
uv run python switch_provider.py switch openrouter

# List available providers
uv run python switch_provider.py list
```

### 4. Test Connection
```bash
# Use included test client
uv run python examples/websocket_client.py

# Test provider switching
uv run python examples/provider_switching_demo.py

# Or test actions
uv run python examples/test_router_actions.py
```

## Development Commands

```bash
# Code quality
./scripts/lint.sh              # Run linting and formatting
uv run -m pytest               # Run test suite
uv run -m pytest --cov=src     # Run tests with coverage

# Dependencies
uv add package-name             # Add new dependency
uv sync --strict                # Sync from lockfile

# Server endpoints
curl http://127.0.0.1:8000/health                    # Health check
wscat -c ws://127.0.0.1:8000/ws/chat                 # WebSocket test
```

## Configuration

- **`config.yaml`** - System configuration (host, port, timeouts, gateway settings)
- **`runtime_config.yaml`** - Runtime provider selection and model configurations
- **`.env`** - API keys only (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY)
- **Server**: `http://127.0.0.1:8000`
- **WebSocket**: `ws://127.0.0.1:8000/ws/chat`

### Runtime Configuration Features
- **Immediate Provider Switching**: Change AI providers without restarting the server
- **Automatic Reloading**: Configuration changes are detected and applied automatically
- **Strict Mode**: No fallbacks - fail fast behavior for reliable operation
- **Per-Provider Models**: Configure different models for each AI provider

### Provider Switching
```bash
# Command-line switching
uv run python switch_provider.py switch openai

# Or edit runtime_config.yaml directly
provider: "anthropic"  # openai, anthropic, gemini, openrouter
strict_mode: true
```

For detailed architecture, communication protocols, and implementation guidelines, see [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md).
