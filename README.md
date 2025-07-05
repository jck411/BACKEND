
# Backend Project

> Flexible, LAN-only backend for streaming AI-generated text/images to multiple client UIs, centralizing all model/device settings, and supporting multiple inference providers and home automation. See `PROJECT_OVERVIEW.md` for full architecture and details.

## Features
- WebSocket streaming to UIs (Web, Kivy, PySide)
- Central MCP service (profiles, config, chat, devices)
- Multiple AI providers (OpenAI, Anthropic, local LLMs)
- Zigbee home automation (via adapters)
- Aggregator: proxy/aggregate 100s of external MCP servers (ON/OFF, static config)
- Hot-reload config via Redis Pub/Sub

## Quickstart
1. Pin Python version (see `pyproject.toml`).
2. Install dependencies (from lockfile):
   ```bash
   uv sync --strict
   ```
3. Copy and edit config:
   ```bash
   cp .env.example .env
   # Edit config.yaml as needed
   ```
4. Start the server:
   ```bash
   uv run src/gateway/main.py
   ```
5. Run linting and tests:
   ```bash
   ./scripts/lint.sh
   uv run -m pytest
   ```

## Project Structure
- `src/gateway/`   – WebSocket endpoint, auth
- `src/router/`    – Orchestrator logic
- `src/adapters/`  – AI provider & Zigbee plugins
- `src/mcp/`       – Model-Context Protocol service & aggregator
- `src/common/`    – Shared types, config loader, logging
- `tests/`         – Unit/integration tests (pytest, pytest-asyncio)
- `scripts/`       – Linting, dev start scripts

## Communication Protocols
- Client ↔ Gateway: WebSockets
- Gateway ↔ Router: Direct calls or gRPC
- Router ↔ Adapters: gRPC streams
- Router ↔ MCP: REST/JSON or gRPC
- MCP Updates → Router: Redis Pub/Sub
- Adapters → Devices: MQTT (Zigbee2MQTT)

## Engineering Rules (Summary)
- Pin interpreter version; never mix versions
- Add dependencies with `uv add`; always commit lockfile
- Use async/event-driven design; never block main thread
- Single responsibility per file; avoid god classes
- Never commit secrets; read from environment
- ≥ 40% test coverage on critical logic; lint/type-check in CI
- Structured JSON logs; no metrics endpoints
- Optimise only after profiling; set realistic SLOs
- Fail fast on invalid input; catch broad exceptions only at process boundaries

See `PROJECT_RULES.md` for full rules and development standards.

