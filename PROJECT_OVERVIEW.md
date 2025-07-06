# Project Overview

A LAN-only backend that streams AI-generated content to multiple clients over WebSockets, with centralized configuration management via Model-Context Protocol (MCP).

## 1. Purpose

- **WebSocket Streaming**: Real-time AI text/images to multiple client UIs (Kivy, PySide, web)
- **MCP-Centric Architecture**: Centralized tool registry with vendor-agnostic tool definitions
- **Multi-Provider Support**: OpenAI, Anthropic, Gemini, OpenRouter with unified MCP tool interface
- **Dynamic Tool Discovery**: Runtime tool registration via standard MCP protocol
- **Home Automation via MCP**: Zigbee device control managed as MCP tools/services

## 2. Current Implementation Status

### ✅ Production-Ready Features
- **WebSocket Gateway**: FastAPI-based streaming with connection management
- **Multi-Provider AI**: OpenAI, Anthropic, Gemini, OpenRouter with <1ms chunk forwarding
- **Runtime Switching**: Instant provider changes via `runtime_config.yaml` (no restart)
- **Standard MCP Server**: POST `/tools/list` and POST `/tools/call` endpoints following MCP 2025 specification
- **MCP Tool Registry**: Vendor-agnostic tool discovery with runtime registration and validation
- **AI Self-Configuration Tool**: Natural language parameter adjustment via MCP ("make it creative" → temp↑)
- **External MCP Compatibility**: Works with claude-desktop, VS Code MCP extensions, any MCP client
- **High-Performance Streaming**: Zero-delay content forwarding, no duplication
- **Comprehensive Testing**: Real API integration, MCP compliance verification, external client testing

### 🔄 Planned Features
- **MCP Aggregator Server**: Multi-server aggregation with local/remote tool bridging
- **Home Automation MCP Tools**: Zigbee device control via MCP tool definitions (not direct MQTT)
- **LLM-Enhanced Interpretation**: Replace pattern matching with LLM-based tool understanding
- **Dynamic Tool Visibility**: User-based tool access with OAuth 2.1 scopes and Resource Indicator flow
- **Context-Aware Tool Suggestion**: Intelligent tool recommendation based on conversation context

## 3. Architecture

```
Client UIs ──── WebSocket ──▶ Gateway ──▶ Router ──▶ LLM Adapters ──▶ AI Providers
                     │             │           │            │
                     ▼             │           │            └──▶ MCP Tool Registry
                 Logging/Metrics   │           │                       │
                                   │           └─ pulls tools ──────────┤
                                   │                                    ├─ Local Tools (stdio)
                                   └──▶ MCP Aggregator ◄─────────────────┤
                                              │                         └─ External MCP Servers (HTTP Streaming)
                                              │
                                              └──▶ Home Automation MCP Tools
                                                   Smart Home Control via MCP
```

### MCP Infrastructure Components

**1. Central MCP Tool Registry (Runtime-Configurable)**
- Single, vendor-agnostic source of truth for tool definitions
- Tools defined in MCP-native schema (Tool, ToolParameter, etc.)
- Runtime tool discovery via `list_tools()` and execution via `execute_tool()`
- Input validation with categories, examples, and constraints
- Built-in tools with lazy registration

**2. MCP Aggregator Server (Planned)**
- Bridges local and remote tool registries
- Merges tools from local MCP registry (stdio) and external MCP servers (HTTP streaming)
- Handles name-spacing and filtering (e.g., `github_search`, `local_search`)
- Routes tool calls to appropriate handlers or proxies
- Optional higher-order tools: `batch_execute`, `search_tools`

**3. LLM Adapters (Per Provider)**
- Adapts central tool definitions to model-specific schemas:
  - OpenAI: `{"name", "description", "parameters"}`
  - Claude: `{"name", "description", "input_schema"}`
  - Gemini: `functionDeclarations`
- **Pulls tools from registry** and injects into LLM request payloads
- Routes tool calls back through aggregator to MCP registry
- **Orchestrator layer** - LLMs never directly access `/tools/list`

**4. Transport Layer (MCP 2025 Specification)**
| Component | Role | Protocol |
|-----------|------|----------|
| LLM Adapter ⇄ Local MCP Registry | Fastest, tight loop for tool calls | **stdio (JSON over stdin/stdout)** |
| LLM Adapter ⇄ Aggregated MCP | Broader reach, dynamic tools | **HTTP Streaming (chunked/ndjson)** |
| Aggregator ⇄ Public MCPs | Proxy to external sources | **HTTPS (MCP 2025 spec, Resource Indicator OAuth)** |

- **Gateway**: WebSocket connections, authentication, message framing
- **Router**: Request orchestration, timeout handling, streaming coordination
- **LLM Adapters**: Provider-specific tool injection and response handling
- **MCP Registry**: Centralized tool definitions with runtime discovery
- **MCP Aggregator**: Local and remote tool bridging (planned)

## 4. Project Structure

```
BACKEND/
├── src/
│   ├── main.py              # Application entry point
│   ├── gateway/             # WebSocket endpoint & connection management
│   ├── router/              # Request orchestration & adapter coordination
│   ├── adapters/            # AI provider adapters (OpenAI, Anthropic, etc.)
│   ├── mcp/                 # Model-Context Protocol service
│   │   ├── mcp_server.py           # Standard MCP HTTP endpoints
│   │   ├── self_config_service.py  # AI parameter configuration
│   │   └── tools/                  # MCP tool implementations
│   └── common/              # Shared models, config, logging
├── tests/                   # Unit & integration tests
├── examples/                # WebSocket clients, demos, provider switching
├── scripts/                 # Lint, start scripts
├── config.yaml              # System configuration
├── runtime_config.yaml      # Runtime provider selection & model settings
└── switch_provider.py       # Command-line provider switching utility
```

## 5. Usage Examples

### WebSocket Client
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/chat');

// Send chat message
ws.send(JSON.stringify({
    action: "chat",
    payload: {text: "Tell me a joke"},
    request_id: "chat-123"
}));

// Receive real-time streaming response
ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    if (response.status === 'chunk') {
        console.log(response.chunk.data); // "Why", " did", " the", " chicken..."
    }
};
```

### Provider Switching
```bash
# Switch providers instantly
python switch_provider.py anthropic
python switch_provider.py gemini
python switch_provider.py --show  # Check current provider
```

### MCP Self-Configuration
```bash
# Standard MCP tool discovery (MCP 2025 spec requires POST)
curl -X POST http://127.0.0.1:8000/tools/list \
  -H "Content-Type: application/json" \
  -H "Accept: application/x-ndjson" \
  -d '{}'

# Standard MCP tool execution
curl -X POST http://127.0.0.1:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ai_configure",
    "arguments": {
      "request": "Make responses more creative and colorful"
    }
  }'
# → Returns: temperature increased to 0.9, confidence: 85%
```

### Home Automation via MCP (Planned)
```bash
# Home automation as MCP tools
curl -X POST http://127.0.0.1:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "smart_home_control",
    "arguments": {
      "action": "set_lights",
      "room": "living_room",
      "brightness": 80,
      "color": "warm_white"
    }
  }'
# → Zigbee device control via MCP tool interface
```

## 6. Modern MCP Infrastructure

### Tool Call Flow
```
[ LLM ]
   │
   ├─ fetches tools ───────────▶ [ MCP Aggregator ]
   │                             ├─ local tools via HTTP
   │                             └─ remote MCPs via HTTP streaming
   │
   ├─ makes tool call ─────────▶ [ Aggregator routes to correct handler ]
   │
   └─ receives result ─────────▶ continues conversation
```

### LLM-Agnostic Architecture
```
┌─────────────────┐    ┌────────────────────────────────────┐
│ Any LLM Provider│◄───┤ MCP Protocol Layer                 │
│ (OpenAI,        │────►  - Standard tool discovery       │
│  Anthropic,     │    │  - Vendor-agnostic tool registry  │
│  Gemini, etc.)  │    │  - Runtime tool registration      │
└─────────────────┘    └─────────────┬──────────────────────┘
                                     │
                       ┌─────────────▼──────────────────────┐
                       │ MCP Tool Registry                  │
                       │ - AI self-configuration tools      │
                       │ - Home automation MCP tools        │
                       │ - External MCP server aggregation  │
                       └─────────────────────────────────────┘
```

### Key Design Principles
- **Universal Compatibility**: Works with any LLM provider via standard MCP protocol
- **Tool-Centric Approach**: Everything (config, automation, etc.) managed as MCP tools
- **Runtime Discovery**: Tools discovered dynamically, not hard-coded
- **Standard Compliance**: Follows MCP 2025 specification for interoperability
- **Aggregation Ready**: Can bridge local and remote MCP tool ecosystems

### MCP Tool Examples
```
AI Configuration Tool:
- Natural language parameter adjustment
- "make it creative" → LLM interprets and adjusts parameters
- Confidence-based decisions with real-time updates

Home Automation Tools (Planned):
- Zigbee device control via MCP tool definitions
- "turn on living room lights" → MCP tool execution
- Device state management through tool registry

External Tool Integration (Planned):
- GitHub search, weather data, calendar management
- Tools from public MCP servers via aggregator
- Name-spaced tool routing and conflict resolution
```

## 7. Performance Metrics

```
OpenAI API Response Time: ~1000ms
Chunk Forwarding Delay: <1ms
Memory Usage: Minimal (no accumulation)
WebSocket Throughput: Real-time streaming
Error Recovery: Automatic with proper logging
```

## 8. Implementation Phases

### Phase 1: Standard MCP Server ✅ Complete
- Standard MCP HTTP endpoints (`/tools/list`, `/tools/call`)
- Vendor-agnostic tool registry with runtime registration
- AI configuration tool with natural language interface
- External MCP client compatibility (claude-desktop, VS Code extensions)
- Comprehensive parameter validation and error handling

### Phase 2: MCP Aggregator Server 🔄 Planned
- Bridge local and remote MCP tool registries
- Tool aggregation from external MCP servers via HTTP streaming
- Name-spacing and conflict resolution for overlapping tools
- Higher-order tools: `batch_execute`, `search_tools`, tool composition
- Caching and performance optimization for remote tool calls

### Phase 3: Home Automation MCP Tools 🔄 Planned
- Zigbee device control via MCP tool definitions (not direct MQTT)
- Smart home tools: lighting, climate, security, entertainment
- Device state management through MCP tool registry
- Natural language device control: "dim the living room lights to 30%"
- Integration with Zigbee2MQTT via MCP tool interface

### Phase 4: Advanced MCP Features 🔄 Planned
- Dynamic user-based tool visibility with OAuth 2.1 Resource Indicator scopes
- Context-aware tool suggestion and auto-completion
- Tool usage analytics and optimization recommendations
- Memoization for deterministic tools and caching strategies

## Planned Future Capabilities

### OAuth 2.1 Resource Indicator Support
```yaml
# OAuth 2.1 Resource Indicator for secure external MCP discovery
oauth:
  resource_indicator: "mcp://homeassistant.local:8123/tools"
  scope: "tools:list tools:call"
  grant_type: "authorization_code"
```

### Multi-Provider Tool Synthesis
- **Cross-Provider Reasoning**: Combine OpenAI's code generation with Claude's analysis
- **Tool Chain Orchestration**: Sequence tools across different providers
- **Result Aggregation**: Merge outputs from multiple AI providers

### Enterprise Features
- **Multi-Tenant Architecture**: Separate tool namespaces per tenant
- **Audit Logging**: Complete request/response logging for compliance
- **Rate Limiting**: Per-provider and per-tool rate limiting
- **Health Monitoring**: Provider health checks and automatic failover

## 9. Engineering Standards

- **Async/Event-Driven**: All I/O operations use async/await
- **Type Safety**: Comprehensive type hints and Pydantic validation
- **Structured Logging**: JSON logs with timing and performance metrics
- **Error Handling**: Fail fast on invalid input, graceful degradation
- **Testing**: ≥40% coverage with real API integration tests
- **Code Quality**: Ruff linting, Black formatting, pre-commit hooks

For complete guidelines, see [`PROJECT_RULES.md`](PROJECT_RULES.md).
