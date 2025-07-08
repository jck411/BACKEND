# MCP Dynamic Configuration - Development Summary

## Quick Overview
The backend now uses MCP 2025 server as the single source of truth for LLM configuration. The LLM can configure itself dynamically through natural language using MCP tools.

## Architecture (Simplified)
```
User Request → LLM → MCP Tools → MCP Server → Configuration Change → Persistence
                ↓
         "I've updated my settings..."
```

## Key Implementation Details

### 1. MCP Server is Configuration Authority
- **File**: `src/mcp/mcp2025_server.py`
- **Methods**: `get_active_provider_config()`, `set_provider_parameter()`, `switch_active_provider()`
- **Role**: Single source of truth for all LLM configuration

### 2. Runtime Config is Just Persistence
- **File**: `src/common/runtime_config.py`
- **Class**: `RuntimeConfigPersistence`
- **Role**: Only saves/loads `runtime_config.yaml`, no logic

### 3. MCP Configuration Tools
Located in `src/mcp/tools/`:
- `ai_configure` - Main tool for parameter changes
- `show_current_config` - Display current settings
- `list_available_models` - Show available models
- `switch_provider` - Change AI provider
- `parameter_info` - Show parameter constraints
- `reset_config` - Reset to defaults

### 4. All Adapters Use MCP Server
Each adapter (`openai_adapter.py`, `anthropic_adapter.py`, etc.) fetches config from MCP server via `_get_config()` method.

### 5. Router Integration
`src/router/request_router.py`:
- Gets active provider from MCP server
- Passes MCP server instance to adapters
- Fails if MCP server unavailable

## How It Works

1. **User says**: "Make me more creative"
2. **LLM interprets** and calls: `ai_configure(parameter='temperature', value='0.8')`
3. **MCP tool executes**: Updates configuration in MCP server
4. **MCP server**: Saves to `runtime_config.yaml`
5. **LLM responds**: "I've increased my creativity settings..."

## Testing Scenarios (Phase 9 - TODO)

### Basic Tests
```bash
python src/main.py
```

Then via WebSocket:
- "Make me more creative" → Should increase temperature
- "Be more focused" → Should decrease temperature
- "Show my settings" → Should display configuration
- "Switch to Claude" → Should ask confirmation, then switch

### Edge Cases to Test
- Invalid model names
- Out-of-range parameters
- Provider without API key
- Configuration persistence across restarts

## Common Development Tasks

### Add New Configuration Parameter
1. Update parameter schemas in `src/mcp/parameter_schemas.py`
2. Add to `get_parameter_constraints()` in MCP server
3. Update adapters to use new parameter

### Add New Provider
1. Create adapter in `src/adapters/`
2. Add to router initialization
3. Add parameter schemas
4. Update available providers list

### Debug Configuration Issues
1. Check logs for `mcp_server` events
2. Verify `runtime_config.yaml` contents
3. Test with `show_current_config` tool

## File Structure
```
src/
├── mcp/
│   ├── mcp2025_server.py      # Configuration authority
│   ├── tools/                  # MCP configuration tools
│   └── tool_registry.py        # Tool management
├── adapters/                   # Provider adapters (all use MCP)
├── router/
│   └── request_router.py       # Routes requests, uses MCP
├── common/
│   └── runtime_config.py       # File persistence only
└── main.py                     # Startup with MCP health checks
```

## Important Notes
- **No self-configuration service** - LLM uses tools directly
- **Fail-fast design** - System won't start without MCP server
- **Single source of truth** - MCP server only
- **Natural language** - LLM interprets user intent

## Next Steps
1. Run comprehensive tests (Phase 9)
2. Update documentation (Phase 10)
3. Add more sophisticated parameter constraints
4. Consider adding configuration history/rollback

---
*Last Updated: 2025-07-08*
*Status: Implementation complete, ready for testing*
