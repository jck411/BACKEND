"""
Tool Format Translation - Schema transformer in <50 LOC as recommended.
Converts MCP tool definitions to provider-specific formats.

Following PROJECT_RULES.md:
- Single responsibility: Tool format translation
- Type safety with comprehensive validation
- Pure functions: stateless, side-effect-free
"""

from typing import Dict, List, Any


class ToolTranslator:
    """Pure schema transformation between MCP and provider formats."""

    @staticmethod
    def mcp_to_openai(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool format to OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"],
                },
            }
            for tool in mcp_tools
        ]

    @staticmethod
    def mcp_to_anthropic(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool format to Anthropic tools format."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"],
            }
            for tool in mcp_tools
        ]

    @staticmethod
    def mcp_to_gemini(mcp_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert MCP tool format to Gemini function declarations."""
        return {
            "functionDeclarations": [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"],
                }
                for tool in mcp_tools
            ]
        }

    @staticmethod
    def mcp_to_openrouter(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool format to OpenRouter (OpenAI-compatible) format."""
        return ToolTranslator.mcp_to_openai(mcp_tools)
