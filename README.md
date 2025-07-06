
# Backend Project

> Flexible, LAN-on## Commands

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
```treaming AI-generated content to multiple client UIs over WebSockets. See [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) for full architecture, features, and implementation details.

## Current Status
✅ **Working WebSocket Gateway** with request routing, connection management, and structured logging
🔄 **Planned**: MCP service, AI adapters, home automation, aggregation features

## Quick Start

### 1. Setup Environment
```bash
# Install dependencies
uv sync --strict

# Copy environment template (optional)
cp .env.example .env
```

### 2. Start Server
```bash
# Start server
uv run python src/main.py

# Or use script
./scripts/start_dev.sh
```

### 3. Test Connection
```bash
# Use included test client
uv run python examples/websocket_client.py

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

- **`config.yaml`** - Main configuration (host, port, timeouts)
- **`.env`** - Environment variables (optional overrides)
- **Server**: `http://127.0.0.1:8000`
- **WebSocket**: `ws://127.0.0.1:8000/ws/chat`

For detailed architecture, communication protocols, and implementation guidelines, see [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md).
