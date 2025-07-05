Project Overview

This document provides a high-level overview of the backend project, explaining its purpose, main components, folder structure, and how to get started.

1. Purpose

The backend project implements a flexible, LAN-only backend that:

Streams AI-generated text or images to multiple client UIs (e.g., Kivy, PySide, web) over WebSockets.

Centralizes all model and device settings in a single MCP (Model-Context Protocol) service, so inference parameters and home-automation commands are managed in one place.

Supports multiple inference providers (OpenAI, Anthropic, local LLM) and home-automation via Zigbee, with clean separation between components.

2. High-Level Architecture

Client UIs  ─── WebSocket ──▶ Gateway ──▶ Router ──▶ Adapters ──▶ Providers/Zigbee
                       │            │
                       │            └──▶ MCP (config & profiles)
                       ▼
                   Logging
                   Metrics

Gateway: Accepts client connections, handles authentication, and frames WebSocket messages.

Router: Directs requests by fetching the correct settings from MCP, choosing the right adapter, and streaming results back to the client, including timeout and fallback logic.

Adapters: One per external system, translating between internal requests and provider APIs or device commands.

MCP: Single source of truth for model parameters, user profiles, device definitions, and chat history.

Providers/Zigbee: The actual AI services (e.g., OpenAI) and home-automation hub that carry out inference or device control.

3. Folder Structure

backend/
├── README.md         # Quickstart and overview
├── pyproject.toml    # Dependencies and tooling config
├── .env.example      # Environment variables template
├── config.yaml       # Single configuration for all components
│
├── src/              # Main application code
│   ├── gateway/      # WebSocket endpoint and auth
│   ├── router/       # Orchestrator logic
│   ├── adapters/     # Plugins for AI providers and Zigbee
│   ├── mcp/          # Model-Context Protocol service
│   └── common/       # Shared types, utilities, and settings loader
│
├── tests/            # Unit and integration tests
└── scripts/          # Helper scripts (lint, start)

4. Key Components

config.yaml: Holds all settings (database path, API keys, default model parameters).

gateway/: Implements FastAPI WebSocket route; validates incoming frames and sends outgoing chunks.

router/: Core logic for fetching MCP profiles, invoking adapters, and managing streams and error handling.

adapters/: Modules (openai_adapter.py, anthropic_adapter.py, local_llm_adapter.py, zigbee_adapter.py) that interface with each external system.

mcp/: Model-Context Protocol service following the latest MCP specification (see docs/mcp_spec.md or official documentation). Uses SQLite initially to store CRUD operations on model profiles, user and device settings, and chat history, and broadcasts updates via pub/sub.

  • Aggregator: Can proxy/aggregate 100s of external MCP servers (e.g., context7, memorybank), with ON/OFF toggles and static config in config.yaml. Broadcasts updates from external MCPs. Conflict resolution/schema is LLM-driven. Enables large-scale, flexible context/memory scenarios.

common/: Houses Pydantic models (e.g., Chunk), logging setup, and the loader that reads config.yaml and .env.: Houses Pydantic models (e.g., Chunk), logging setup, and the loader that reads config.yaml and .env.

tests/: Organized to mirror src/, using pytest and pytest-asyncio for async components.

scripts/: lint.sh to run Ruff & Black, start_dev.sh to launch all components locally.

5. Communication Protocols & Connections

Client ↔ Gateway: Uses WebSockets for persistent, bidirectional streaming of text tokens or image bytes between UI and server.

Gateway ↔ Router: In a single-process setup, this can be direct function calls; for distributed services, use gRPC (HTTP/2 + Protobuf) to enforce schemas and enable low-latency streaming.

Router ↔ Adapters: Communicates over gRPC streams, converting internal request objects into provider-specific API streams and back.

Router ↔ MCP: Fetches and updates profiles via RESTful HTTP/JSON (or gRPC for stricter contracts), keeping configuration human-readable and easy to debug.

MCP Updates → Router: Uses a lightweight Redis Pub/Sub channel so routers hot-reload parameter changes without restarts.

Adapters → Devices: For home-automation commands, uses MQTT over TCP (via Zigbee2MQTT) at defined QoS levels to ensure reliable delivery.

6. Current Working Implementation (Added 2025-07-05)

The system now has a working bare-bones implementation with Router integration:

**Architecture Clarification:**

*Device Control Flow:*
1. User: "Turn on the lights" → Frontend → WebSocket → Backend
2. Backend LLM processes request and calls device functions directly
3. Backend executes device commands via Zigbee adapter
4. Backend sends status update to frontend: "Lights turned on"
5. Frontend displays confirmation to user

*Audio Streaming Flow:*
1. Backend generates TTS audio data
2. Backend streams audio chunks to frontend via WebSocket
3. Frontend plays audio in real-time
4. Supports various audio formats and voice configurations

*Frontend Command Flow:*
1. Backend determines UI updates needed (notifications, status displays)
2. Backend sends frontend_command actions to update UI
3. Frontend handles display logic and user experience

**Message Flow:**
1. Client connects to WebSocket endpoint: `ws://127.0.0.1:8000/ws/chat`
2. Client sends action message with proper payload structure
3. Gateway parses message and routes to Router
4. Router processes request type and executes appropriate backend logic
5. Router streams chunked responses back through Gateway
6. Client receives real-time streaming responses

**Supported Actions:**
- `chat`: Text generation/conversation with LLM function calling for device control
- `generate_image`: Image generation requests (placeholder responses)
- `audio_stream`: Audio data streaming for TTS/speech synthesis
- `frontend_command`: UI-specific commands (notifications, display updates, etc.)

**Example Client Interaction:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/chat');

// Text chat with potential device control via LLM function calling
ws.send(JSON.stringify({
    action: "chat",
    payload: {text: "Turn on the living room lights and tell me about the weather"},
    request_id: "chat-123"
}));

// Audio streaming for TTS output
ws.send(JSON.stringify({
    action: "audio_stream",
    payload: {text: "Hello, this will be converted to speech", voice: "en-US-male"},
    request_id: "audio-456"
}));

// Frontend-specific commands (notifications, UI updates)
ws.send(JSON.stringify({
    action: "frontend_command",
    payload: {command: "show_notification", data: {message: "Device status updated"}},
    request_id: "ui-789"
}));
```

**What's Working:**
✅ FastAPI WebSocket Gateway with connection management
✅ Router with request orchestration and timeout handling
✅ Structured JSON logging with performance timing
✅ Type-safe message validation with Pydantic
✅ Real-time response streaming to client
✅ Pre-commit hooks for code quality
✅ Proper architecture separation: backend handles device control via LLM function calling
✅ Audio streaming capability for TTS and voice synthesis
✅ Frontend command system for UI updates and notifications

**Architecture Principles:**
- Device control happens on backend via LLM function calling, not frontend execution
- Audio streaming flows from backend to frontend for TTS/speech synthesis
- Frontend receives display commands and notifications, handles UI/UX
- Clear separation of concerns: backend for intelligence, frontend for presentation

**Next Steps:**
- MCP service for user/model profile management
- Real AI adapters (OpenAI, Anthropic, local LLM) with function calling capabilities
- Zigbee adapter for backend device control execution
- TTS/audio generation adapters for voice synthesis
- Authentication and user management
- Frontend client updates to use proper backend protocol
