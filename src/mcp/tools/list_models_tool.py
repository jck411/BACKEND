"""
List Available Models Tool for MCP

This tool lists all available models for each provider
through the standard MCP tool interface.

Standard MCP Tool: list_available_models
- Shows all supported providers
- Lists available models for each provider
- Indicates which model is currently active
- Shows model support status
"""

from typing import Dict, Any

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from common.logging import get_logger

logger = get_logger(__name__)


class ListModelsTool(ToolHandler):
    """
    Standard MCP tool for listing available AI models.

    Provides comprehensive list of all supported models
    across all providers with their availability status.
    """

    def __init__(self, mcp_server):
        """Initialize the list models tool."""
        self.mcp_server = mcp_server
        logger.info(event="list_models_tool_initialized")

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="list_available_models",
            description="List all available AI models across all supported providers. Shows which models are available and indicates the currently active model.",
            parameters=[
                ToolParameter(
                    name="provider",
                    type=ToolParameterType.STRING,
                    description="Filter results to show models for a specific provider only",
                    required=False,
                    enum=["openai", "anthropic", "gemini", "openrouter"],
                ),
                ToolParameter(
                    name="format",
                    type=ToolParameterType.STRING,
                    description="Output format for the model list",
                    required=False,
                    default="grouped",
                    enum=["grouped", "flat", "json"],
                ),
            ],
            examples=[
                "list_available_models()",
                "list_available_models(provider='openai')",
                "list_available_models(format='flat')",
                "list_available_models(provider='anthropic', format='json')",
            ],
            category="ai_configuration",
            version="1.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the list available models tool.

        Args:
            arguments: Tool arguments containing optional 'provider' and 'format'

        Returns:
            List of available models with their status
        """
        try:
            filter_provider = arguments.get("provider")
            output_format = arguments.get("format", "grouped")

            logger.info(
                event="list_models_tool_executed",
                filter_provider=filter_provider,
                format=output_format,
            )

            # Get current configuration to identify active model
            current_config = await self.mcp_server.get_active_provider_config()
            active_provider = current_config.get("provider")
            active_model = current_config.get("model")

            # Get list of available providers
            providers = await self.mcp_server.get_available_providers()

            # Filter providers if requested
            if filter_provider:
                if filter_provider in providers:
                    providers = [filter_provider]
                else:
                    return {
                        "status": "error",
                        "error": f"Provider '{filter_provider}' not found",
                        "message": f"Available providers: {', '.join(providers)}",
                        "tool": "list_available_models",
                    }

            # Collect models for each provider
            all_models = {}
            total_count = 0

            for provider in providers:
                models_info = await self.mcp_server.get_available_models(provider)
                all_models[provider] = models_info["models"]
                total_count += len(models_info["models"])

            # Format output based on requested format
            if output_format == "json":
                # Raw JSON format
                formatted_output = {
                    "providers": {},
                    "active": {
                        "provider": active_provider,
                        "model": active_model,
                    },
                }

                for provider, models in all_models.items():
                    formatted_output["providers"][provider] = [
                        {
                            "name": model["name"],
                            "supported": model["supported"],
                            "active": (
                                provider == active_provider and model["name"] == active_model
                            ),
                        }
                        for model in models
                    ]

            elif output_format == "flat":
                # Flat list format
                lines = [
                    "Available AI Models:",
                    f"Active: {active_provider}/{active_model}",
                    "",
                ]

                for provider, models in all_models.items():
                    for model in models:
                        is_active = provider == active_provider and model["name"] == active_model
                        status = " ✓" if is_active else ""
                        lines.append(f"  {provider}/{model['name']}{status}")

                formatted_output = "\n".join(lines)

            else:  # grouped format
                # Grouped by provider format
                lines = [
                    "🤖 Available AI Models",
                    "=" * 50,
                    f"Current: {active_provider} - {active_model}",
                    "",
                ]

                for provider, models in all_models.items():
                    is_active_provider = provider == active_provider
                    provider_header = f"📦 {provider.upper()}"
                    if is_active_provider:
                        provider_header += " (active)"

                    lines.append(provider_header)
                    lines.append("-" * len(provider_header))

                    for model in models:
                        is_active = is_active_provider and model["name"] == active_model
                        status = ""
                        if is_active:
                            status = " ✓ (current)"
                        elif not model["supported"]:
                            status = " ⚠️ (limited support)"

                        lines.append(f"  • {model['name']}{status}")

                    lines.append("")

                lines.append(f"Total: {total_count} models across {len(all_models)} providers")
                lines.append("")
                lines.append("💡 Use 'switch_provider' to change providers")

                formatted_output = "\n".join(lines)

            result = {
                "status": "success",
                "models": formatted_output if isinstance(formatted_output, str) else None,
                "data": formatted_output if isinstance(formatted_output, dict) else None,
                "message": f"Found {total_count} models across {len(all_models)} providers",
                "active_provider": active_provider,
                "active_model": active_model,
                "tool": "list_available_models",
            }

            logger.info(
                event="list_models_completed",
                total_models=total_count,
                providers_count=len(all_models),
                format=output_format,
            )

            return result

        except Exception as e:
            logger.error(
                event="list_models_tool_error",
                error=str(e),
            )

            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to list models: {str(e)}",
                "tool": "list_available_models",
            }
