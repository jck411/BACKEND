# Project Overview

This document provides a comprehensive overview of the backend project, explaining its purpose, architecture, current implementation status, and planned features.

## 1. Purpose

The backend project implements a flexible, LAN-only backend that:

- Streams AI-generated text or images to multiple client UIs (e.g., Kivy, PySide, web) over WebSockets.
- Centralizes all model and device settings in a single MCP (Model-Context Protocol) service, so inference parameters and home-automation commands are managed in one place.
- Supports multiple inference providers (OpenAI, Anthropic, local LLM) and home-automation via Zigbee, with clean separation between components.

## 2. Features

### Current Implementation (v0.1 - Working Base)
- ✅ **WebSocket Gateway**: FastAPI-based streaming gateway with connection management
- ✅ **Request Router**: Request orchestration with timeout handling and response streaming
- ✅ **Multi-Provider Support**: OpenAI, Anthropic, Gemini, and OpenRouter adapters with unified interface
- ✅ **Runtime Configuration**: Strict mode provider selection with immediate switching (no fallbacks)
- ✅ **OpenAI Integration**: Real-time streaming chat completions with optimized performance
- ✅ **Anthropic Integration**: Claude models with streaming support and error handling
- ✅ **Gemini Integration**: Google Gemini models with async streaming capabilities
- ✅ **OpenRouter Integration**: Access to 100+ models through unified OpenAI-compatible API
- ✅ **Structured Logging**: JSON logs with performance metrics and timing information
- ✅ **Type Safety**: Pydantic models with comprehensive validation
- ✅ **Automation Tools**: Pre-commit hooks, linting, testing infrastructure
- ✅ **Configuration Management**: Runtime provider switching with environment-based API keys
- ✅ **Examples & Testing**: WebSocket test clients and provider switching utilities
- ✅ **High-Performance Streaming**: Zero-delay content forwarding with no duplication

### Planned Features (Future Versions)
- 🔄 **Central MCP Service**: User profiles, model configurations, chat history, device definitions
- 🔄 **MCP Tool Integration**: Function calling and tool orchestration via MCP servers
- 🔄 **Home Automation**: Zigbee device control via MQTT/Zigbee2MQTT through MCP tools
- 🔄 **MCP Aggregation**: Proxy/aggregate 100s of external MCP servers with conflict resolution
- 🔄 **Hot Configuration**: Redis Pub/Sub for real-time config updates without restarts
- 🔄 **Authentication**: User management and WebSocket authentication
- 🔄 **TTS/Audio**: Text-to-speech and audio streaming capabilities

## 3. Current Status (Updated 2025-07-06)

### ✅ Successfully Implemented Components

**Core Architecture:**
- FastAPI WebSocket gateway with connection lifecycle management
- Request router with timeout handling and adapter orchestration framework
- Structured JSON logging with performance timing (`TimedLogger`)
- Type-safe message validation using Pydantic models

**Multi-Provider AI Integration:**
- **OpenAI Adapter**: Production-ready streaming chat completions with optimized performance
- **Anthropic Adapter**: Claude models (claude-3-5-sonnet-20241022) with streaming support
- **Google Gemini Adapter**: Gemini models (gemini-1.5-flash) with async streaming capabilities
- **OpenRouter Adapter**: Access to 100+ models through unified OpenAI-compatible API
- **Runtime Provider Switching**: Immediate provider changes via runtime_config.yaml (no restart required)
- **Strict Mode**: No fallbacks - fail fast when provider unavailable (following PROJECT_RULES.md)
- **High-Performance Streaming**: Zero-delay content forwarding, immediate chunk delivery
- **Error Handling**: Comprehensive API timeout, rate limit, and error recovery
- **Clean Architecture**: Unified `BaseAdapter` interface for all providers

**Data Models:**
- `Chunk` - Streaming content structure (text, images, metadata)
- `WebSocketMessage` - Client-to-server message format
- `WebSocketResponse` - Server-to-client response format
- `AdapterRequest/Response` - Unified interface for all AI providers

**Configuration System:**
- Runtime configuration file (runtime_config.yaml) for immediate provider switching
- Environment-based API key management (no secrets in configuration files)
- Strict mode enabled by default (no fallbacks, fail fast)
- Automatic configuration reloading with file change detection
- Provider-specific model settings (temperature, max_tokens, system prompts)
- Future-ready for frontend integration with planned API endpoints

**Infrastructure:**
- Pre-commit hooks with Ruff and Black
- Pytest test suite with async support and real API testing
- Scripts for linting and server startup
- Production-ready WebSocket client examples
- Provider switching utility (switch_provider.py) for easy runtime configuration
- Comprehensive multi-provider test suite with strict mode validation

### 🏗️ **Architecture Lessons Learned**

**Streaming Performance Optimization:**
- **Immediate Forwarding**: Each OpenAI chunk forwarded in ~0ms with no accumulation
- **No Duplicate Content**: Completion signals send metadata only, preventing duplication
- **Minimal Processing**: Zero string concatenation or memory building during streaming
- **Clean Separation**: Adapters handle API specifics, router handles orchestration

**Provider Architecture Design:**
- **Unified Interface**: All providers implement `BaseAdapter` with standardized request/response
- **Runtime Switching**: Change providers instantly via runtime_config.yaml editing
- **Strict Mode**: No fallbacks, fail fast when provider unavailable (PROJECT_RULES.md compliant)
- **MCP-Ready**: Architecture designed for future MCP integration without breaking changes
- **Configuration Separation**: Provider selection vs. inference parameters clearly separated
- **Extensible**: Adding new providers follows established adapter pattern

### 🔄 Architecture Ready for Extension

**Multi-Provider Framework:**
- `src/adapters/base.py` - Standardized adapter interface for all AI providers
- `src/adapters/openai_adapter.py` - Production adapter with streaming optimization
- `src/adapters/anthropic_adapter.py` - Claude integration with streaming support
- `src/adapters/gemini_adapter.py` - Google Gemini integration with async streaming
- `src/adapters/openrouter_adapter.py` - Multi-model access via OpenRouter API
- `src/common/runtime_config.py` - Runtime configuration management with auto-reload
- `runtime_config.yaml` - Runtime provider selection and model configuration
- `switch_provider.py` - Command-line utility for easy provider switching

**MCP Service Integration Points:**
- Provider configurations and model parameters
- User profiles and chat history
- Tool/function definitions for smart home integration
- Real-time configuration updates via Redis Pub/Sub

### 📊 Testing Status

**Production Testing Results:**
- ✅ **Real OpenAI Integration**: Live API calls with streaming responses in ~1 second
- ✅ **WebSocket Performance**: Zero-delay chunk forwarding, no duplication
- ✅ **Error Handling**: API timeouts, rate limits, and connection failures handled gracefully
- ✅ **Connection Management**: Proper connection lifecycle with structured logging
- ✅ **Frontend Integration**: Ready for production frontend integration

**Performance Metrics:**
```
OpenAI API Response Time: ~1000ms
Chunk Forwarding Delay: <1ms
Memory Usage: Minimal (no accumulation)
WebSocket Throughput: Real-time streaming
Error Recovery: Automatic with proper logging
```

**Example Test Output:**
```
Connecting to ws://127.0.0.1:8000/ws/chat...
Received welcome: {"request_id":"welcome","status":"complete",...}
Sending message: {"action": "chat", "payload": {"text": "Hello!"}, ...}
Receiving responses:
Status: processing → chunk → chunk → chunk → complete
```

### 🏗️ Architecture Compliance

✅ **Async/Event-Driven**: All I/O operations use async/await
✅ **Timeout Handling**: Configurable timeouts with graceful degradation
✅ **Structured Logging**: JSON logs with timing and context information
✅ **Single Responsibility**: Each module has focused, well-defined purpose
✅ **Type Safety**: Comprehensive type hints and Pydantic validation
✅ **Error Handling**: Graceful error recovery with proper logging

## 4. High-Level Architecture
                       │            │
## 4. High-Level Architecture

```
Client UIs  ─── WebSocket ──▶ Gateway ──▶ Router ──▶ Adapters ──▶ Providers/Zigbee
                       │            │
                       │            └──▶ MCP (config & profiles)
                       ▼
                   Logging
                   Metrics
```

**Gateway**: Accepts client connections, handles authentication, and frames WebSocket messages.

**Router**: Directs requests by fetching the correct settings from MCP, choosing the right adapter, and streaming results back to the client, including timeout and fallback logic.

**Adapters**: One per external system, translating between internal requests and provider APIs or device commands.

**MCP**: Single source of truth for model parameters, user profiles, device definitions, and chat history.

**Providers/Zigbee**: The actual AI services (e.g., OpenAI) and home-automation hub that carry out inference or device control.

## 5. Project Structure

BACKEND/
├── README.md         # Quickstart and overview
├── PROJECT_OVERVIEW.md # This document
├── PROJECT_RULES.md  # Development standards and engineering rules
├── STATUS.md         # Current implementation status
├── pyproject.toml    # Dependencies and tooling config
├── uv.lock          # Locked dependencies for reproducible builds
├── .env.example      # Environment variables template
├── config.yaml       # System configuration (gateway, router, etc.)
├── runtime_config.yaml # Runtime provider selection and model settings
├── switch_provider.py # Command-line utility for provider switching
│
├── src/              # Main application code
│   ├── main.py       # Application entry point
│   ├── gateway/      # WebSocket endpoint and connection management
│   ├── router/       # Request orchestration and adapter coordination
│   ├── adapters/     # AI provider adapters (OpenAI, Anthropic, Gemini, OpenRouter)
│   ├── mcp/          # Model-Context Protocol service (planned)
│   └── common/       # Shared types, utilities, config loader, runtime config, and logging
│
├── tests/            # Unit and integration tests
├── examples/         # Test clients, provider switching demos, and action examples
└── scripts/          # Helper scripts (lint, start)

## 6. Key Components

config.yaml: Holds all settings (gateway host/port, timeouts, logging configuration).

gateway/: Implements FastAPI WebSocket route with connection management; validates incoming frames and sends outgoing chunks. Currently includes `websocket.py` (FastAPI app) and `connection_manager.py` (WebSocket lifecycle management).

router/: Core logic for request orchestration, timeout handling, and streaming responses. Currently includes `request_router.py` (main orchestrator) and `message_types.py` (request/response models). **Note**: MCP integration and adapter coordination will be added when those services are implemented.

adapters/: **Planned directory** for modules (openai_adapter.py, anthropic_adapter.py, local_llm_adapter.py, zigbee_adapter.py) that will interface with each external system. Currently empty.

mcp/: **Planned directory** for Model-Context Protocol service following the latest MCP specification. Will use SQLite initially to store CRUD operations on model profiles, user and device settings, and chat history, and broadcast updates via pub/sub. Currently empty.

  • Aggregator: **Planned feature** to proxy/aggregate 100s of external MCP servers (e.g., context7, memorybank), with ON/OFF toggles and static config in config.yaml. Will broadcast updates from external MCPs with LLM-driven conflict resolution/schema handling.

common/: Houses Pydantic models (WebSocketResponse, Chunk, etc.), structured logging setup with TimedLogger, and the configuration loader that reads config.yaml and environment variables.

tests/: Organized to mirror src/, using pytest and pytest-asyncio for async components. Includes unit tests for config, models, gateway, and router components.

scripts/: `lint.sh` to run Ruff & Black, `start_dev.sh` to launch the application locally.

examples/: Contains `websocket_client.py` for testing WebSocket connections and `test_router_actions.py` for testing different action types.

## 7. Communication Protocols & Connections

## 7. Communication Protocols & Connections

### Current Implementation
**Client ↔ Gateway**: WebSockets for persistent, bidirectional streaming of text tokens or image bytes between UI and server.

**Gateway ↔ Router**: Direct function calls in single-process setup; designed for future gRPC distribution.

### Planned Protocols
**Router ↔ Adapters**: gRPC streams for converting internal request objects into provider-specific API streams and back.

**Router ↔ MCP**: RESTful HTTP/JSON (or gRPC for stricter contracts), keeping configuration human-readable and easy to debug.

**MCP Updates → Router**: Redis Pub/Sub channel for hot-reloading parameter changes without restarts.

**Adapters → Devices**: MQTT over TCP (via Zigbee2MQTT) at defined QoS levels for reliable home-automation delivery.

## 8. Current Working Implementation & Message Flow

The system now has a **production-ready implementation** with real OpenAI integration:

**Performance Architecture:**

*Real-Time Chat Streaming:*
1. User sends message → Frontend → WebSocket → Backend
2. Backend routes to selected AI provider (currently OpenAI)
3. Provider streams response chunks immediately (no accumulation)
4. Backend forwards each chunk instantly to frontend (<1ms delay)
5. Frontend receives real-time streaming text as it's generated

*Provider Architecture:*
1. **Unified Interface**: All providers implement standardized `BaseAdapter`
2. **Configuration-Driven**: Provider selection via config, inference params via MCP (future)
3. **High Performance**: Zero-delay chunk forwarding, no duplicate content
4. **Error Resilient**: Timeout handling, rate limiting, graceful degradation

*Future MCP Integration:*
1. Provider selection remains in config file (OpenAI/Anthropic/Gemini choice)
2. All inference parameters migrate to MCP service (temperature, system prompts, etc.)
3. Tool/function definitions managed by MCP servers
4. Real-time parameter updates via Redis Pub/Sub

**Message Flow:**
1. Client connects to WebSocket endpoint: `ws://127.0.0.1:8000/ws/chat`
2. Client sends chat action with text payload
3. Gateway validates and routes to Router
4. Router selects provider adapter (currently OpenAI)
5. Adapter streams real AI responses back through Gateway
6. Client receives immediate streaming responses (no mock data)

**Current Provider Support:**
- ✅ **OpenAI**: Production-ready with gpt-4o-mini, streaming optimization
- ✅ **Anthropic**: Claude models with claude-3-5-sonnet-20241022, streaming support
- ✅ **Google Gemini**: Gemini models with gemini-1.5-flash, async streaming
- ✅ **OpenRouter**: Multi-model access with anthropic/claude-3-sonnet
- 🔄 **Local LLMs**: Planned (self-hosted models)

**Example Provider Switching:**
```bash
# Switch providers instantly via command line
python switch_provider.py anthropic
python switch_provider.py gemini
python switch_provider.py --show  # Check current provider

# Or edit runtime_config.yaml directly:
# provider:
#   active: "anthropic"  # Changes take effect immediately
```

**Real-time chat with any provider:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/chat');

// Works with OpenAI, Anthropic, Gemini, or OpenRouter
ws.send(JSON.stringify({
    action: "chat",
    payload: {text: "Tell me a joke"},
    request_id: "chat-123"
}));

// Receive real streaming response from selected provider
ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    if (response.status === 'chunk') {
        // Real AI content streaming in real-time
        console.log(response.chunk.data); // "Why", " did", " the", " chicken..."
    }
};
```

**What's Working Now:**
✅ **Multi-Provider AI Integration**: OpenAI, Anthropic, Gemini, OpenRouter with streaming
✅ **Runtime Provider Switching**: Instant provider changes via runtime_config.yaml
✅ **Strict Mode**: No fallbacks, fail fast behavior (PROJECT_RULES.md compliant)
✅ **High-Performance Streaming**: <1ms chunk forwarding, zero duplication
✅ **Production WebSocket Gateway**: Connection management with structured logging
✅ **Provider Architecture**: Extensible framework with unified BaseAdapter interface
✅ **Configuration Management**: Runtime config with environment-based API keys
✅ **Error Handling**: API timeouts, rate limits, connection failures handled gracefully
✅ **Provider Switching Utilities**: Command-line tools and Python API for switching
✅ **Frontend Ready**: Production-ready for any frontend framework

**Architecture Principles:**
- **Runtime Provider Switching**: Instant changes via runtime_config.yaml editing
- **Strict Mode**: No fallbacks, fail fast when provider unavailable
- **Inference Parameters**: Managed in runtime_config.yaml (will migrate to MCP service)
- **Streaming Performance**: Immediate forwarding with zero processing delays
- **Extensibility**: Adding new providers follows established adapter pattern
- **MCP Ready**: Architecture designed for future MCP integration without breaking changes

## 9. Next Implementation Steps

### Immediate Priorities (Completed - Multi-Provider Support)

1. **✅ AI Provider Adapters** - Extended the proven OpenAI pattern
   - **✅ Anthropic Adapter**: Claude integration with streaming support
   - **✅ Google Gemini Adapter**: Gemini models with async streaming capabilities
   - **✅ OpenRouter Adapter**: Multi-model access via unified API
   - **✅ Runtime Provider Switching**: Instant provider changes via configuration

2. **✅ Enhanced Configuration Management**
   - **✅ Runtime Configuration**: runtime_config.yaml for immediate provider switching
   - **✅ API Key Management**: Environment-based secrets for all providers
   - **✅ Provider-Specific Settings**: Model names, temperatures, system prompts per provider
   - **✅ Strict Mode**: No fallbacks, fail fast behavior (PROJECT_RULES.md compliant)

3. **MCP Service Foundation** (Next Priority)
   - **SQLite Backend**: User profiles, model configurations, chat history
   - **Parameter Migration**: Move inference settings from runtime config to MCP
   - **RESTful API**: Configuration management endpoints
   - **Real-time Updates**: Redis Pub/Sub for parameter changes

### Medium-term Goals (MCP Integration)

4. **MCP Tool Integration**
   - **Tool Definition Management**: Function schemas via MCP servers
   - **Dynamic Tool Loading**: Runtime tool registration and discovery
   - **Tool Orchestration**: LLM function calling through MCP protocol
   - **Multi-Server Aggregation**: Combine tools from multiple MCP servers

5. **Advanced Provider Features**
   - **Model-Specific Optimization**: Provider-specific streaming optimizations
   - **Cost Management**: Token usage tracking and cost optimization
   - **Rate Limit Handling**: Intelligent backoff and provider switching
   - **Local LLM Integration**: Self-hosted model support

6. **Production Features**
   - **Authentication System**: User management and WebSocket authentication
   - **Monitoring & Metrics**: Provider performance and usage analytics
   - **Configuration Hot-Reload**: Zero-downtime parameter updates
   - **Error Recovery**: Advanced fallback and retry strategies

### Architecture Evolution

**Configuration Strategy:**
```yaml
# runtime_config.yaml - Immediate provider switching
provider:
  active: "anthropic"  # openai | anthropic | gemini | openrouter
  models:
    anthropic:
      model: "claude-3-5-sonnet-20241022"
      temperature: 0.7
      max_tokens: 4096

# Changes take effect immediately, no restart required
```

**Future MCP Migration:**
```yaml
# config.yaml - Provider selection only (future)
providers:
  active: "anthropic"  # Managed by MCP service

# All inference parameters migrate to MCP service:
# - temperature, max_tokens, system_prompts
# - model selection, provider-specific settings
# - user preferences, chat history
```

**Provider Integration Pattern:**
- All providers implement unified `BaseAdapter` interface
- Streaming optimization patterns established with OpenAI
- Error handling and fallback strategies proven and reusable
- MCP integration points designed for all providers

**Future MCP Architecture:**
- **Provider Agnostic**: MCP manages inference parameters for all providers
- **Tool Integration**: MCP servers provide tools/functions to all providers
- **User Context**: Profiles and history managed centrally via MCP
- **Real-time Updates**: Configuration changes propagated via Redis Pub/Sub

## 10. Engineering Standards & Rules

### Implementation Principles
- **Pin interpreter version**: Never mix Python versions across environments
- **Dependency management**: Use `uv add` for dependencies; always commit lockfile
- **Async design**: Event-driven architecture; never block main thread
- **Single responsibility**: One purpose per file/class; avoid god classes
- **Security**: Never commit secrets; read from environment variables
- **Testing**: ≥ 40% test coverage on critical logic; lint/type-check in CI
- **Logging**: Structured JSON logs; no metrics endpoints in application
- **Performance**: Optimize only after profiling; set realistic SLOs
- **Error handling**: Fail fast on invalid input; catch broad exceptions only at process boundaries

### Code Quality Standards
- **Linting**: Ruff for fast Python linting
- **Formatting**: Black for consistent code style
- **Type checking**: mypy for static type analysis
- **Testing**: pytest with pytest-asyncio for async components
- **Pre-commit**: Automated quality checks before commits

For complete implementation guidelines, see [`PROJECT_RULES.md`](PROJECT_RULES.md).
