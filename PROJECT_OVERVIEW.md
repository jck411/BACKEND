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
- ✅ **Standard MCP Server**: HTTP endpoints `/tools/list` and `/tools/call` following MCP specification
- ✅ **Vendor-Agnostic Tool Registry**: Runtime tool discovery and parameter validation
- ✅ **AI Self-Configuration Tool**: Natural language parameter adjustment with confidence-based decisions
- ✅ **External MCP Client Compatibility**: Works with claude-desktop, VS Code extensions, and any MCP client

### Planned Features (Future Versions)
- 🔄 **Advanced MCP Features**: Multi-server aggregation and capability conflict resolution
- 🔄 **LLM-Enhanced Interpretation**: Replace pattern matching with actual LLM-based natural language understanding
- 🔄 **User Profiles**: Persistent user preferences and adjustment history
- 🔄 **Frontend Integration**: Rich UI for parameter visualization and manual overrides
- 🔄 **Multi-Model Orchestration**: Coordinate parameters across multiple active models
- 🔄 **Home Automation**: Zigbee device control via MQTT/Zigbee2MQTT through MCP capabilities
- 🔄 **Authentication**: User management and WebSocket authentication
- 🔄 **TTS/Audio**: Text-to-speech and audio streaming capabilities

## 3. Current Status (Updated 2025-01-06)

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

**Standard MCP Implementation:**
- **Standard HTTP Endpoints**: GET `/tools/list` and POST `/tools/call` following MCP specification
- **Vendor-Agnostic Tool Registry**: Runtime tool discovery with parameter validation
- **AI Configuration Tool**: Natural language parameter adjustment with confidence-based decisions
- **External Client Compatibility**: Works with claude-desktop, VS Code MCP extensions, and any MCP client
- **Parameter Validation**: Comprehensive type checking and constraint enforcement
- **Error Handling**: Standard MCP error responses with detailed validation messages
- **Tool Execution**: Real-time tool execution with metadata and performance metrics

**AI Self-Configuration Capability:**
- **Natural Language Processing**: "Make responses more creative" → temperature adjustment
- **Explicit Commands**: "Set temperature to 0.8" → direct parameter setting
- **Contextual Adjustments**: Provider-aware parameter constraints and validation
- **Confidence Framework**: High confidence → apply immediately, low confidence → ask for clarification
- **Real-time Updates**: Changes applied immediately to runtime configuration
- **Multi-Provider Support**: Works seamlessly with OpenAI, Anthropic, Gemini, OpenRouter

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
- **MCP Migration Ready**: Current configuration will be migrated to LLM-agnostic MCP service

**Infrastructure:**
- Pre-commit hooks with Ruff and Black
- Pytest test suite with async support and real API testing
- Scripts for linting and server startup
- Production-ready WebSocket client examples
- Provider switching utility (switch_provider.py) for easy runtime configuration
- Comprehensive multi-provider test suite with strict mode validation

### 🏗️ **MCP Architecture Design (Next Major Feature)**

**Protocol-First Architecture:**
```
┌─────────────┐     ┌──────────────────────────────────────────┐
│ Any LLM     │◄────┤ MCP Protocol Layer (LLM-Agnostic)       │
│ (OpenAI,    │     │ - Standardized messages                  │
│  Anthropic, │─────► - Capability discovery                  │
│  Gemini,    │     │ - Natural language understanding        │
│  Local...)  │     │ - No function calling dependencies      │
└─────────────┘     └───────────────┬──────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │ Semantic Intent Router                   │
                    │ - "make responses colorful" → temp: 0.9 │
                    │ - Vector-based capability matching       │
                    │ - Parameter extraction from natural lang │
                    └───────────────┬──────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │ Dynamic Capability Registry              │
                    │ - Runtime capability registration        │
                    │ - Semantic capability descriptions       │
                    │ - Version management & discovery         │
                    └─────┬─────────┬─────────────┬────────────┘
                          │         │             │
           ┌──────────────▼─┐  ┌────▼──────────┐  ┌▼────────────────┐
           │ Self-Config    │  │ Smart Home    │  │ Future          │
           │ Capability     │  │ Capability    │  │ Capabilities    │
           │ Server         │  │ Server        │  │ (External MCP)  │
           └────────────────┘  └───────────────┘  └─────────────────┘
```

**Key MCP Design Principles:**
- ✅ **LLM-Agnostic**: Works with ANY LLM provider without modification
- ✅ **Protocol-First**: Capabilities defined by semantic descriptions, not function signatures
- ✅ **Natural Language Interface**: "make it colorful" → LLM interprets and chooses parameters
- ✅ **Dynamic Discovery**: LLMs discover available capabilities at runtime
- ✅ **No Function Calling Dependencies**: Uses standardized MCP protocol instead
- ✅ **LLM Intelligence-Based**: No preset mappings - LLM interprets any word/phrase using its intelligence
- ✅ **Probabilistic Decision Making**: LLM confidence levels determine interaction patterns
- ✅ **Context-Aware Constraints**: LLM receives provider-specific parameter limits and current values
- ✅ **Real-time Capability Updates**: Streaming capability changes
- ✅ **Multi-Server Aggregation**: Combine capabilities from multiple MCP servers

**Self-Configuration Example Flow:**
```
User: "Make my responses more whimsical and verbose"
↓
LLM discovers MCP self-config capability via semantic matching
↓
MCP provides: temperature (0.0-1.0, current: 0.7), max_tokens (1-4096, current: 2048)
↓
LLM confidence assessment:
- "whimsical" → 85% confidence → higher temperature
- "verbose" → 90% confidence → more tokens
↓
LLM interprets: whimsical=creative=temp:0.9, verbose=longer=tokens:3000
↓
LLM calls MCP: adjust_parameters(temperature=0.9, max_tokens=3000)
↓
MCP validates against Anthropic constraints and applies changes
↓
Response: "I've made myself more whimsical (temp: 0.9) and verbose (3000 tokens)!"
```

**Probabilistic Decision Framework:**
```
High Confidence (>80%): Act immediately
- "Make it more creative" → Increase temperature

Medium Confidence (40-80%): Act with explanation
- "Turn it up to 11" → Set to max + explain assumption

Low Confidence (<40%): Ask for clarification + show options
- "Set temperature to banana" → "I'm not sure what 'banana' means. Current range is 0.0-1.0..."

Explicit Wild Request: Go creative even with low confidence
- "Give me a wild guess" → Make creative choice + explain reasoning
```

**Benefits of MCP Architecture:**
- **Universal Compatibility**: Same system works with OpenAI, Anthropic, Gemini, local models
- **No Provider-Specific Code**: Eliminates need for function calling implementations per provider
- **Infinite Vocabulary**: LLM interprets ANY descriptive word using its intelligence
- **Intelligent Constraint Handling**: LLM receives context about provider limits and makes informed decisions
- **Confidence-Based Interactions**: High confidence → act immediately, low confidence → ask for clarification
- **Dynamic Extensibility**: Add new capabilities without changing core system
- **Real-time Updates**: Configuration changes propagate immediately

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

**MCP Service Integration Architecture:**
- **Protocol Layer**: LLM-agnostic capability discovery and execution
- **Semantic Router**: Natural language to capability mapping ("colorful" → temperature)
- **Capability Registry**: Dynamic registration and versioning of capabilities
- **Self-Configuration Capability**: AI model parameter modification via natural language
- **Smart Home Capability**: Device control via semantic understanding
- **Real-time Updates**: Streaming capability and configuration changes

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
│   ├── mcp/          # Model-Context Protocol service with standard endpoints
│   │   ├── mcp_server.py     # Standard MCP HTTP server (/tools/list, /tools/call)
│   │   ├── tool_registry.py  # Vendor-agnostic tool registry with validation
│   │   ├── self_config_service.py  # AI parameter configuration service
│   │   ├── connection_manager.py   # MCP capability management (legacy)
│   │   ├── parameter_schemas.py    # Provider parameter definitions
│   │   └── tools/               # MCP tool implementations
│   │       └── ai_config_tool.py   # AI configuration tool for MCP
│   └── common/       # Shared types, utilities, config loader, runtime config, and logging
│
├── tests/            # Unit and integration tests
├── examples/         # Test clients, provider switching demos, and action examples
│   ├── websocket_client.py         # WebSocket test client
│   ├── simple_mcp_demo.py         # Standalone MCP self-configuration demo
│   ├── mcp_websocket_integration.py  # WebSocket + MCP integration demo
│   ├── mcp_standard_client_test.py   # Standard MCP HTTP endpoints test
│   ├── external_mcp_integration.py   # External MCP client compatibility demo
│   ├── provider_switching_demo.py    # Provider switching examples
│   └── test_router_actions.py       # Router action testing
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

## 9. MCP Implementation Strategy (2025 Best Practices)

### Core Architecture Principles

**Protocol-First Design:**
- Define capability interface before implementation details
- Use semantic capability descriptions instead of function signatures
- Focus on natural language understanding over rigid APIs
- Design for protocol evolution and versioning

**LLM-Agnostic Foundation:**
```
┌─────────────────┐    ┌──────────────────────────────────────┐
│ Any LLM Provider│    │ MCP Protocol Layer                   │
│ - OpenAI        │◄───┤ - Capability discovery              │
│ - Anthropic     │────►  - Natural language interpretation  │
│ - Gemini        │    │  - Semantic parameter mapping       │
│ - Local models  │    │  - Real-time streaming updates      │
└─────────────────┘    └─────────────┬────────────────────────┘
                                     │
                       ┌─────────────▼────────────────────────┐
                       │ Intelligent Decision Engine          │
                       │ - LLM interprets ANY word/phrase     │
                       │ - Confidence-based action patterns   │
                       │ - Context-aware constraint handling  │
                       │ - Provider limitation awareness      │
                       └─────────────┬────────────────────────┘
                                     │
                       ┌─────────────▼────────────────────────┐
                       │ Dynamic Capability Registry          │
                       │ - Runtime capability registration    │
                       │ - Semantic descriptions & examples   │
                       │ - Version management & discovery     │
                       └──┬────────┬────────┬─────────────────┘
                          │        │        │
              ┌───────────▼──┐ ┌───▼─────┐ ┌▼─────────────────┐
              │ Self-Config  │ │ Smart   │ │ Future External  │
              │ Capability   │ │ Home    │ │ MCP Servers      │
              │ Server       │ │ Control │ │ (Aggregation)    │
              └──────────────┘ └─────────┘ └──────────────────┘
```

### Implementation Phases

**Phase 1: Comprehensive Parameter Schema & Popular Models (Week 1-2)**
- **Enhanced Runtime Config**: Complete parameter schemas for all providers based on official API documentation
- **Popular Model Support**: Focus on most-used models initially
  - OpenAI: `gpt-4o`, `gpt-4o-mini`, `o1-preview`, `o1-mini` (reasoning models)
  - Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`
  - Gemini: `gemini-1.5-flash`, `gemini-1.5-pro`
  - OpenRouter: Model categorization system for Claude-like, GPT-like patterns
- **Full Parameter Support**: temperature, max_tokens, top_p, top_k, penalties, seed, response_format, stop sequences
- **Provider-Specific Constraints**: Accurate parameter ranges and model-specific limitations
- **Natural Language Parameter Adjustment**: LLM interprets descriptive terms and applies appropriate values
- **Confidence-Based Decision Making**: High confidence → act, low confidence → ask for clarification

**Phase 2: Dynamic Capability Registry (Week 3-4)**
- **Protocol-First Capability Definition**: Standardized capability discovery and execution
- **Runtime Capability Registration**: Add/remove capabilities without restart
- **Vector-Based Intent Matching**: Natural language to capability mapping
- **Capability Versioning**: Backward compatibility and schema evolution

**Phase 3: Multi-Server Aggregation (Month 2)**
- **External MCP Server Integration**: Proxy and aggregate external MCP servers
- **Capability Conflict Resolution**: Handle overlapping capabilities intelligently
- **Real-Time Updates**: Streaming capability and configuration changes
- **Load Balancing**: Failover and performance optimization for capability services

### Key Technical Decisions

**Why Protocol-First MCP vs Function Calling:**
- ✅ **Universal Compatibility**: Works with any LLM without provider-specific implementations
- ✅ **Natural Language Interface**: Users can express intent naturally without learning APIs
- ✅ **Infinite Vocabulary**: LLM interprets ANY word/phrase using its intelligence (no preset mappings)
- ✅ **Intelligent Decision Making**: LLM confidence levels determine interaction patterns
- ✅ **Context-Aware Constraints**: LLM receives provider-specific limits and makes informed decisions
- ✅ **Dynamic Extensibility**: Add capabilities without changing core system
- ✅ **Real-time Updates**: Configuration changes propagate immediately
- ✅ **Future-Proof**: Easy to integrate with external MCP servers

**Example Natural Language Self-Configuration:**
```
User: "Make my responses more effervescent and laconic"
↓
MCP provides capability context: temperature (0.0-1.0), max_tokens (1-4096), system_prompt
↓
LLM confidence assessment:
- "effervescent" → 75% confidence (bubbly/lively = creative = higher temp)
- "laconic" → 90% confidence (brief/concise = fewer tokens)
↓
LLM reasoning: effervescent=lively=temp:0.85, laconic=brief=tokens:800
↓
LLM calls: adjust_parameters(temperature=0.85, max_tokens=800)
↓
Response: "Made myself more effervescent (temp: 0.85) and laconic (max: 800 tokens)!"

Alternative - Low Confidence Example:
User: "Set temperature to rainbow"
↓
LLM confidence: 15% (unclear what rainbow means for temperature)
↓
Response: "I'm not sure what 'rainbow' means for temperature! 🌈
Current options for Anthropic:
• Temperature range: 0.0-1.0 (currently 0.7)
• 0.0-0.3: Very focused and precise
• 0.4-0.6: Balanced responses
• 0.7-1.0: More creative and varied
What temperature level were you thinking?"
```

**Technical Implementation:**
- **Capability Discovery**: LLMs query available capabilities with current constraints and context
- **Intelligent Interpretation**: LLM uses its knowledge to understand ANY descriptive term
- **Confidence Assessment**: LLM evaluates certainty before acting or asking for clarification
- **Context-Aware Constraints**: Provider-specific limits and current values provided in real-time
- **Probabilistic Action Patterns**: High confidence → act, medium → act+explain, low → ask
- **Real-time Updates**: Streaming configuration changes without restarts
- **Provider Agnostic**: Same system works with OpenAI, Anthropic, Gemini, local models

## 10. Potential Advanced Integrations

Beyond the core self-configuration MCP service, the LLM + MCP architecture opens up fascinating possibilities for leveraging advanced reasoning capabilities:

### **1. Meta-Cognitive Reasoning with Uncertainty**
Rather than simple confidence scores, advanced MCP implementations can support **explicit uncertainty representation**. LLMs can reason about their own knowledge gaps and actively request targeted information.

```
User: "Is this code secure?"
LLM: "I see potential SQL injection in line 17, but I'm uncertain about the authentication protocol used. Should I request the auth implementation details?"
```

### **2. Recursive Self-Improvement Loops**
LLMs can analyze their own outputs and iteratively improve them when given appropriate MCP structures:

```
Initial response → Self-critique → MCP-mediated revision → Improved response
```

This creates a "reasoning cascade" where each iteration improves upon the previous one.

### **3. Multi-Agent Reasoning Networks**
Specialized agent collectives with differentiated roles through MCP:

- **Critic Agent**: Challenges assumptions and identifies logical flaws
- **Researcher Agent**: Gathers supporting evidence and counterarguments
- **Synthesizer Agent**: Creates coherent narratives from multiple perspectives
- **Coordinator Agent**: Manages collaboration flow and resolves conflicts

### **4. Probabilistic Program Synthesis**
Instead of deterministic tool execution, LLMs can generate probabilistic programs through MCP that explore multiple solution paths simultaneously:

```python
# LLM-generated probabilistic program via MCP
def solve_problem(input):
    solutions = []
    # Branch 1: Statistical approach (70% confidence)
    solutions.append(statistical_solution(input))
    # Branch 2: Symbolic reasoning (50% confidence)
    solutions.append(symbolic_solution(input))
    # Branch 3: Neural approach (85% confidence)
    solutions.append(neural_solution(input))
    return weighted_ensemble(solutions)
```

### **5. Causal Reasoning Frameworks**
MCP-enabled LLMs can reason explicitly about causality rather than just correlation:

```
User: "Sales dropped last month."
LLM identifies potential causal factors through MCP-enabled analysis:
1. Seasonal effects (85% confidence)
2. Price increase (70% confidence)
3. Competitor promotion (40% confidence)
Then suggests experiments to disambiguate causes.
```

### **6. Compositional Reasoning with Verifiability**
Breaking complex reasoning into atomic, verifiable steps:

```
Complex problem → MCP decomposes into sub-problems → External verification of each step → Composed solution with proof trail
```

Each reasoning step produces a verifiable artifact that external systems can validate.

### **7. Reasoning over Heterogeneous Knowledge Structures**
LLMs can reason across different knowledge representation formats through MCP:

- Graph databases for relationships
- Vector embeddings for semantic similarity
- Symbolic logic for formal reasoning
- Temporal sequences for event analysis

### **8. Adaptive Chain-of-Thought Prompting**
Dynamic, adaptive reasoning paths based on problem complexity:

```
Initial problem → MCP analyzes complexity → Tailors reasoning approach:
- Simple issue: Direct response
- Complex calculation: Step-by-step mathematical reasoning
- Ambiguous question: Clarification dialogue
- Multi-faceted problem: Parallel exploration of approaches
```

### **Key Patterns for Advanced LLM + MCP Integration:**

**Multi-Step Reasoning Chains:**
- LLM breaks complex requests into logical steps
- Each step can invoke different MCP capabilities
- Results feed forward to inform subsequent decisions

**Context-Aware Adaptability:**
- LLM considers current state, constraints, and goals
- Adapts strategy based on available resources and capabilities
- Makes trade-off decisions with reasoning transparency

**Emergent Capability Composition:**
- LLM combines simple MCP capabilities in novel ways
- Creates sophisticated workflows from basic building blocks
- Discovers new use patterns not explicitly programmed

**Intelligent Error Handling & Recovery:**
- LLM reasons about failure modes and alternative approaches
- Gracefully degrades when certain capabilities are unavailable
- Learns from failures to improve future decisions

**Natural Language Interfaces to Complex Systems:**
- Users express high-level intent in natural language
- LLM translates to specific system actions and configurations
- Provides human-readable explanations of what was done and why

This approach transforms MCP from just a configuration protocol into a **reasoning amplification platform** - where LLMs become intelligent orchestrators that can understand context, make complex decisions, and adapt their behavior based on available capabilities and constraints.

## 11. Phase 1 Implementation: Comprehensive Parameter Support

### **Provider Parameter Research (Based on Official APIs)**

**OpenAI Models:**
```yaml
Standard Models (gpt-4o, gpt-4o-mini, gpt-4-turbo):
  temperature: {min: 0.0, max: 2.0, default: 1.0}
  max_tokens: {min: 1, max: 4096, default: null}
  top_p: {min: 0.0, max: 1.0, default: 1.0}
  frequency_penalty: {min: -2.0, max: 2.0, default: 0.0}
  presence_penalty: {min: -2.0, max: 2.0, default: 0.0}
  seed: {type: integer, default: null}
  response_format: {enum: [text, json_object, json_schema], default: text}
  stop: {type: array, max_items: 4, default: null}

Reasoning Models (o1-preview, o1-mini):
  max_completion_tokens: {min: 1, max: 32768, default: null}
  # NO temperature, top_p, penalties - reasoning models use fixed parameters
  # NO streaming support - responses are generated in full
```

**Anthropic Claude Models:**
```yaml
claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022:
  temperature: {min: 0.0, max: 1.0, default: 1.0}
  max_tokens: {min: 1, max: 4096, default: 4096, required: true}
  top_p: {min: 0.0, max: 1.0, default: null}
  top_k: {min: 1, max: 200, default: null}
  stop_sequences: {type: array, max_items: 4, default: null}
  system: {type: string, default: null}
```

**Google Gemini Models:**
```yaml
gemini-1.5-flash, gemini-1.5-pro:
  temperature: {min: 0.0, max: 1.0, default: 1.0}
  max_output_tokens: {min: 1, max: 8192, default: null}
  top_p: {min: 0.0, max: 1.0, default: null}
  top_k: {min: 1, max: 40, default: null}
  candidate_count: {min: 1, max: 8, default: 1}
  stop_sequences: {type: array, default: null}
  safety_settings: {type: object, default: null}
  response_mime_type: {enum: [text/plain, application/json], default: text/plain}
```

**OpenRouter Models (Model-Dependent):**
```yaml
# Model categorization for parameter inheritance
claude_models: # anthropic/claude-*
  temperature: {min: 0.0, max: 1.0, default: 1.0}
  max_tokens: {min: 1, max: 4096, default: 4096}
  top_p: {min: 0.0, max: 1.0, default: null}
  top_k: {min: 1, max: 200, default: null}
  stop: {type: array, default: null}

gpt_models: # openai/gpt-*
  temperature: {min: 0.0, max: 2.0, default: 1.0}
  max_tokens: {min: 1, max: 4096, default: null}
  top_p: {min: 0.0, max: 1.0, default: 1.0}
  frequency_penalty: {min: -2.0, max: 2.0, default: 0.0}
  presence_penalty: {min: -2.0, max: 2.0, default: 0.0}
  stop: {type: array, default: null}

unknown_models: # Conservative fallback
  temperature: {min: 0.0, max: 1.0, default: 0.7}
  max_tokens: {min: 1, max: 2048, default: 2048}
```

### **Enhanced Runtime Configuration Architecture**

**Static Parameter Schemas (runtime_config.yaml):**
- Complete parameter definitions with accurate constraints
- Model-specific parameter support (reasoning models vs standard models)
- Provider-specific parameter names and ranges
- Default values based on official API documentation

**Dynamic Parameter Values (MCP Service):**
- Current active parameter values for the session
- Natural language adjustment history
- User preference profiles
- Real-time parameter validation and application

### **Natural Language Parameter Interpretation Examples**

```
User: "Make responses more creative and detailed"
↓
LLM Analysis:
- "creative" → higher temperature (confidence: 90%)
- "detailed" → more tokens (confidence: 95%)
↓
Provider-Aware Adjustment:
- OpenAI: temperature=1.3, max_tokens=3000
- Anthropic: temperature=0.9, max_tokens=3000 (clamped to max 1.0)
- Gemini: temperature=0.9, max_output_tokens=4000
↓
Response: "Increased creativity and detail! OpenAI temp→1.3, Anthropic temp→0.9 (max), tokens→3000+"
```

```
User: "Reduce randomness and add some repetition penalty"
↓
LLM Analysis:
- "reduce randomness" → lower temperature (confidence: 95%)
- "repetition penalty" → frequency_penalty (confidence: 85%)
↓
Provider-Aware Adjustment:
- OpenAI: temperature=0.3, frequency_penalty=0.5 ✅
- Anthropic: temperature=0.3, frequency_penalty=N/A ❌
↓
Response: "Reduced randomness (temp→0.3). Note: Anthropic doesn't support repetition penalties, but reduced temperature will help."
```

### **Implementation Priority: Popular Models First**

**Phase 1 Model Support:**
1. **OpenAI**: `gpt-4o-mini` (current default), `gpt-4o`, `o1-preview`, `o1-mini`
2. **Anthropic**: `claude-3-5-sonnet-20241022` (current default), `claude-3-5-haiku-20241022`
3. **Gemini**: `gemini-1.5-flash` (current default), `gemini-1.5-pro`
4. **OpenRouter**: Pattern-based categorization for `anthropic/claude-*`, `openai/gpt-*` models

**Expansion Strategy:**
- Start with these 8-10 most popular models
- Add comprehensive parameter support for each
- Build pattern recognition for OpenRouter model categorization
- Gradually expand to more models based on usage patterns

This approach gives us immediate value with the most commonly used models while establishing the architecture for comprehensive model support.

## 11.1. Phase 1 Implementation Status ✅ COMPLETED

**Goal**: Implement basic MCP self-configuration for popular models with natural language parameter adjustment.

### ✅ Completed Components:

1. **Parameter Schemas** (`src/mcp/parameter_schemas.py`)
   - Comprehensive parameter definitions for all providers
   - Support for OpenAI (standard + reasoning), Anthropic, Gemini, OpenRouter
   - Type validation and constraint enforcement
   - Popular models mapping for Phase 1 focus

2. **Self-Configuration Service** (`src/mcp/self_config_service.py`)
   - Natural language parameter interpretation with confidence scoring
   - Pattern matching for creative/conservative/balanced adjustments
   - Explicit value parsing (e.g., "set temperature to 0.8")
   - Confidence-based decision framework:
     - High confidence (>80%): Apply immediately
     - Medium confidence (40-80%): Apply with explanation
     - Low confidence (<40%): Ask for clarification
   - Provider-aware parameter validation and constraints

3. **MCP Connection Manager** (`src/mcp/connection_manager.py`)
   - Capability discovery and management
   - Request routing to appropriate services
   - Integration with WebSocket gateway
   - Error handling and status management

4. **Router Integration** (`src/router/request_router.py`)
   - Added MCP_REQUEST message type
   - Integrated MCP manager with existing request flow
   - WebSocket response formatting for MCP results

5. **Runtime Configuration** (`src/common/runtime_config.py`)
   - Added `update_parameter()` method for MCP integration
   - Async parameter updates with file persistence
   - Cache invalidation for immediate effect

6. **Demo Implementation** (`examples/mcp_self_config_demo.py`)
   - Complete demonstration of MCP capabilities
   - Natural language test cases
   - Confidence scoring examples
   - Configuration state tracking

### ✅ Working Features:

- **Natural Language Processing**: "Make responses more creative" → temperature adjustment
- **Explicit Commands**: "Set temperature to 0.8" → direct parameter setting
- **Contextual Adjustments**: Provider-aware parameter constraints
- **Confidence Framework**: Automatic vs. manual approval based on certainty
- **Real-time Updates**: Changes applied immediately to runtime configuration
- **Error Handling**: Graceful degradation with helpful error messages

### ✅ Supported Models (Phase 1):

**OpenAI**: gpt-4o-mini, gpt-4o, o1-preview, o1-mini
**Anthropic**: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
**Google**: gemini-1.5-flash, gemini-1.5-pro
**OpenRouter**: Pattern-based popular model support

### 🎯 Example Usage:

```python
# Natural language parameter adjustment
result = await mcp_service.execute_natural_language_adjustment(
    "Make responses more creative and colorful"
)
# → Increases temperature, adds explanation

# Explicit parameter setting
result = await mcp_service.execute_natural_language_adjustment(
    "Set temperature to 0.9"
)
# → Sets temperature=0.9 with high confidence

# Vague request handling
result = await mcp_service.execute_natural_language_adjustment(
    "Make it better"
)
# → Requests clarification with available options
```

### 🚀 Ready for Testing:

```bash
# Run the Phase 1 demo (simplified version - works standalone)
python examples/simple_mcp_demo.py

# Integration testing (requires full application context)
# - Start the FastAPI server with: python src/main.py
# - Send MCP_REQUEST via WebSocket with natural language commands
# - Parameters update in real-time via runtime_config.yaml
```

### 🔧 Production Integration:

**WebSocket Message Format:**
```json
{
  "type": "mcp_request",
  "request_id": "req-123",
  "action": "execute",
  "capability_id": "ai_self_configuration",
  "parameters": {
    "request": "Make responses more creative and colorful",
    "context": {"user_preference": "creative_mode"}
  }
}
```

**Response Format:**
```json
{
  "type": "mcp_response",
  "request_id": "req-123",
  "status": "applied",
  "result": {
    "status": "applied",
    "confidence": 0.85,
    "adjustments": {"temperature": 1.2},
    "message": "✅ Increased creativity (temperature: 0.7 → 1.2)"
  }
}
```

### 🎯 Next Phase Recommendations:

1. **LLM-Enhanced Interpretation**: Replace pattern matching with actual LLM-based natural language understanding
2. **Advanced Capabilities**: Add model switching, system prompt modification, function calling configuration
3. **User Profiles**: Persistent user preferences and adjustment history
4. **Frontend Integration**: Rich UI for parameter visualization and manual overrides
5. **Multi-Model Orchestration**: Coordinate parameters across multiple active models

### 🌟 Modern MCP Implementation Approach

Based on current MCP standards and patterns, implementing a vendor-agnostic runtime discovery system:

#### **Vendor-Agnostic Runtime Discovery Pattern**
- **Standard MCP Endpoints**: `/tools/list` and `/tools/call` following MCP protocol
- **Runtime Tool Translation**: Dynamic capability discovery at call-time, not build-time
- **Provider-Agnostic Adapters**: Thin adapters for each LLM provider with standardized interfaces
- **Dynamic Tool Registry**: Real-time capability discovery without hard-coded schemas

#### **Implementation Strategy**
1. **Standard MCP Interface Layer**
   - Implement `/tools/list` endpoint for runtime capability discovery
   - Implement `/tools/call` endpoint for standardized tool execution
   - Provider-specific parameter translation at call-time

2. **Vendor-Agnostic Adapter Pattern**
   - Thin adapters for OpenAI, Anthropic, Gemini, OpenRouter
   - Standardized internal tool representation
   - Runtime parameter mapping and validation

3. **Dynamic Configuration Integration**
   - System prompts as part of dynamic configuration (not hard-coded)
   - Runtime provider switching with capability preservation
   - Context-aware parameter optimization

This approach ensures true MCP compliance while maintaining our multi-provider flexibility and dynamic configuration capabilities.

## 12. Next Implementation Steps

### Immediate Priorities (Next: MCP Protocol Implementation)

1. **🔄 LLM-Agnostic MCP Protocol Layer**
   - **Protocol Definition**: Standardized capability discovery and execution messages
   - **Semantic Capability Registry**: Natural language capability descriptions
   - **Intent Router**: Vector-based matching of natural requests to capabilities
   - **Real-time Streaming**: Bidirectional capability and configuration updates

2. **🔄 AI Self-Configuration Capability**
   - **Natural Language Parameter Updates**: "make responses effervescent" → LLM interprets and adjusts
   - **Infinite Vocabulary Support**: LLM handles ANY descriptive word using its intelligence
   - **Probabilistic Decision Framework**: Confidence-based action patterns (act/explain/ask)
   - **Context-Aware Constraints**: LLM receives provider limits and current values
   - **Universal Provider Support**: Works with OpenAI, Anthropic, Gemini, local models
   - **Immediate Effect Application**: Configuration changes take effect instantly

3. **🔄 Dynamic Capability Management**
   - **Runtime Registration**: Capabilities can be added/removed without restart
   - **Version Management**: Capability versioning and backward compatibility
   - **Conflict Resolution**: Handle overlapping capabilities intelligently
   - **External Server Integration**: Proxy and aggregate external MCP servers

### Medium-term Goals (MCP Integration)

4. **LLM-Agnostic MCP Protocol Implementation**
   - **Protocol-First Design**: Standardized capability discovery and execution
   - **Semantic Capability Registry**: Natural language capability descriptions
   - **Intent Router**: Vector-based matching of natural requests to capabilities
   - **Dynamic Capability Registration**: Runtime registration and versioning

5. **AI Self-Configuration Capability**
   - **Natural Language Parameter Updates**: "make responses more effervescent" → LLM interprets and adjusts
   - **Infinite Vocabulary Support**: LLM handles ANY descriptive word using its intelligence
   - **Probabilistic Decision Framework**: Confidence-based interaction patterns
   - **Context-Aware Constraints**: LLM receives provider-specific limits and current values
   - **Real-time Configuration Changes**: Immediate effect application
   - **Universal Provider Support**: Works with OpenAI, Anthropic, Gemini, local models

6. **Advanced MCP Features**
   - **Multi-Server Aggregation**: Combine capabilities from external MCP servers
   - **Capability Conflict Resolution**: Handle overlapping capabilities intelligently
   - **Streaming Capability Updates**: Real-time capability and configuration changes
   - **Version Management**: Capability versioning and backward compatibility

### Architecture Evolution

**Current Configuration Strategy:**
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

**Future MCP Architecture:**
```yaml
# config.yaml - Provider selection only (future)
providers:
  active: "anthropic"  # Basic provider selection

# MCP Protocol handles all inference parameters:
# ✅ LLM-agnostic capability discovery
# ✅ Natural language configuration: "make it colorful" → temp: 0.9
# ✅ Dynamic capability registration and versioning
# ✅ Semantic intent routing and parameter extraction
# ✅ Real-time streaming updates without restarts
```

**MCP Implementation Benefits:**
- **Universal Compatibility**: Same system works with any LLM provider
- **No Function Calling Dependencies**: Uses standardized MCP protocol
- **Infinite Vocabulary**: LLM interprets ANY descriptive word using its intelligence
- **Intelligent Constraint Handling**: LLM receives context about provider limits and makes informed decisions
- **Confidence-Based Interactions**: High confidence → act, low confidence → ask for clarification
- **Dynamic Extensibility**: Add capabilities without changing core system
- **Real-time Updates**: Configuration and capability changes stream immediately

**Provider Integration Pattern:**
- All providers implement unified `BaseAdapter` interface
- Streaming optimization patterns established with OpenAI
- Error handling and fallback strategies proven and reusable
- **MCP Ready**: Architecture designed for LLM-agnostic capability integration

**MCP Architecture Principles:**
- **LLM-Agnostic**: Works with any provider without modification
- **Protocol-First**: Capabilities defined semantically, not by function signatures
- **Natural Language Interface**: Users express intent in natural language
- **Dynamic Discovery**: LLMs discover capabilities at runtime
- **Semantic Routing**: Vector-based matching of requests to capabilities
- **Real-time Updates**: Configuration and capability changes stream immediately

## 13. Engineering Standards & Rules

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
