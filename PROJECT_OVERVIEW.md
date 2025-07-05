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

