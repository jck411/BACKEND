"""
Switch Provider Tool for MCP

This tool switches the active AI provider with confirmation
through the standard MCP tool interface.

Standard MCP Tool: switch_provider
- Switches between providers (OpenAI, Anthropic, Gemini, OpenRouter)
- Requires explicit confirmation
- Shows current vs new provider details
- Validates provider availability
"""

from typing import Dict, Any

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from common.logging import get_logger

logger = get_logger(__name__)


class SwitchProviderTool(ToolHandler):
    """
    Standard MCP tool for switching AI providers.

    Provides controlled provider switching with validation
    and user confirmation requirements.
    """

    def __init__(self, mcp_server):
        """Initialize the switch provider tool."""
        self.mcp_server = mcp_server
        logger.info(event="switch_provider_tool_initialized")

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="switch_provider",
            description="Switch the active AI provider. Requires confirmation before making the change. Shows comparison between current and target provider.",
            parameters=[
                ToolParameter(
                    name="provider",
                    type=ToolParameterType.STRING,
                    description="Target provider to switch to",
                    required=True,
                    enum=["openai", "anthropic", "gemini", "openrouter"],
                ),
                ToolParameter(
                    name="confirm",
                    type=ToolParameterType.BOOLEAN,
                    description="Explicit confirmation to proceed with the switch",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="model",
                    type=ToolParameterType.STRING,
                    description="Optional: specific model to use with the new provider",
                    required=False,
                ),
            ],
            examples=[
                "switch_provider(provider='anthropic')",
                "switch_provider(provider='openai', confirm=true)",
                "switch_provider(provider='gemini', model='gemini-1.5-pro', confirm=true)",
            ],
            category="ai_configuration",
            version="1.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the switch provider tool.

        Args:
            arguments: Tool arguments containing 'provider', optional 'confirm' and 'model'

        Returns:
            Switch result or confirmation request
        """
        try:
            target_provider = arguments["provider"]
            confirmed = arguments.get("confirm", False)
            target_model = arguments.get("model")

            logger.info(
                event="switch_provider_tool_executed",
                target_provider=target_provider,
                confirmed=confirmed,
                target_model=target_model,
            )

            # Get current configuration
            current_config = await self.mcp_server.get_active_provider_config()
            current_provider = current_config.get("provider")
            current_model = current_config.get("model")

            # Check if already on target provider
            if current_provider == target_provider and not target_model:
                return {
                    "status": "no_change",
                    "message": f"Already using {target_provider}",
                    "current_provider": current_provider,
                    "current_model": current_model,
                    "tool": "switch_provider",
                }

            # Validate target provider
            available_providers = await self.mcp_server.get_available_providers()
            if target_provider not in available_providers:
                return {
                    "status": "error",
                    "error": f"Provider '{target_provider}' not available",
                    "message": f"Available providers: {', '.join(available_providers)}",
                    "tool": "switch_provider",
                }

            # Get available models for target provider
            models_info = await self.mcp_server.get_available_models(target_provider)
            available_models = [m["name"] for m in models_info["models"]]

            # Determine target model
            if target_model:
                # Validate specified model
                if target_model not in available_models:
                    return {
                        "status": "error",
                        "error": f"Model '{target_model}' not available for {target_provider}",
                        "message": f"Available models: {', '.join(available_models)}",
                        "tool": "switch_provider",
                    }
                final_model = target_model
            else:
                # Use first available model as default
                final_model = available_models[0] if available_models else None
                if not final_model:
                    return {
                        "status": "error",
                        "error": f"No models available for {target_provider}",
                        "tool": "switch_provider",
                    }

            # If not confirmed, return confirmation request
            if not confirmed:
                comparison_lines = [
                    "🔄 Provider Switch Request",
                    "=" * 50,
                    "",
                    "Current Configuration:",
                    f"  Provider: {current_provider}",
                    f"  Model: {current_model}",
                    "",
                    "Target Configuration:",
                    f"  Provider: {target_provider}",
                    f"  Model: {final_model}",
                    "",
                    "⚠️  This will change the AI provider for all future interactions.",
                    "",
                    "To confirm, use: switch_provider(provider='"
                    + target_provider
                    + "', confirm=true)",
                ]

                return {
                    "status": "confirmation_required",
                    "message": "\n".join(comparison_lines),
                    "current_provider": current_provider,
                    "current_model": current_model,
                    "target_provider": target_provider,
                    "target_model": final_model,
                    "tool": "switch_provider",
                }

            # Execute the switch
            success = await self.mcp_server.switch_active_provider(target_provider)

            if success:
                # Update model if different from current default
                if target_model:
                    await self.mcp_server.set_provider_parameter(
                        target_provider, "model", final_model
                    )

                result_lines = [
                    "✅ Provider switched successfully!",
                    "",
                    f"Previous: {current_provider} ({current_model})",
                    f"Current: {target_provider} ({final_model})",
                    "",
                    "The new provider is now active for all interactions.",
                ]

                result = {
                    "status": "success",
                    "message": "\n".join(result_lines),
                    "previous_provider": current_provider,
                    "previous_model": current_model,
                    "current_provider": target_provider,
                    "current_model": final_model,
                    "tool": "switch_provider",
                }

                logger.info(
                    event="provider_switched",
                    from_provider=current_provider,
                    to_provider=target_provider,
                    from_model=current_model,
                    to_model=final_model,
                )

                return result

            else:
                return {
                    "status": "error",
                    "error": "Failed to switch provider",
                    "message": "Provider switch failed. Please check logs for details.",
                    "tool": "switch_provider",
                }

        except Exception as e:
            logger.error(
                event="switch_provider_tool_error",
                error=str(e),
                target_provider=arguments.get("provider"),
            )

            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to switch provider: {str(e)}",
                "tool": "switch_provider",
            }
