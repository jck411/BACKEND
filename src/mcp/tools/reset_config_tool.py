"""
Reset Configuration Tool for MCP

This tool resets AI configuration to defaults
through the standard MCP tool interface.

Standard MCP Tool: reset_config
- Resets all parameters to defaults
- Can reset specific provider or current provider
- Requires confirmation
- Shows before/after comparison
"""

from typing import Dict, Any

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from common.logging import get_logger

logger = get_logger(__name__)


class ResetConfigTool(ToolHandler):
    """
    Standard MCP tool for resetting AI configuration.

    Provides controlled reset to default settings
    with confirmation requirements.
    """

    def __init__(self, mcp_server):
        """Initialize the reset config tool."""
        self.mcp_server = mcp_server
        logger.info(event="reset_config_tool_initialized")

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="reset_config",
            description="Reset AI configuration parameters to their default values. Requires confirmation before making changes.",
            parameters=[
                ToolParameter(
                    name="provider",
                    type=ToolParameterType.STRING,
                    description="Provider to reset. Uses current provider if not specified.",
                    required=False,
                    enum=["openai", "anthropic", "gemini", "openrouter", "all"],
                ),
                ToolParameter(
                    name="confirm",
                    type=ToolParameterType.BOOLEAN,
                    description="Explicit confirmation to proceed with the reset",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="parameters",
                    type=ToolParameterType.ARRAY,
                    description="Specific parameters to reset. If not provided, all parameters will be reset.",
                    required=False,
                    items=ToolParameter(
                        name="parameter",
                        type=ToolParameterType.STRING,
                        description="Parameter name to reset",
                    ),
                ),
            ],
            examples=[
                "reset_config()",
                "reset_config(confirm=true)",
                "reset_config(provider='openai', confirm=true)",
                "reset_config(parameters=['temperature', 'max_tokens'], confirm=true)",
                "reset_config(provider='all', confirm=true)",
            ],
            category="ai_configuration",
            version="1.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the reset config tool.

        Args:
            arguments: Tool arguments containing optional 'provider', 'confirm', and 'parameters'

        Returns:
            Reset result or confirmation request
        """
        try:
            specified_provider = arguments.get("provider")
            confirmed = arguments.get("confirm", False)
            specific_params = arguments.get("parameters", [])

            logger.info(
                event="reset_config_tool_executed",
                provider=specified_provider,
                confirmed=confirmed,
                specific_params=specific_params,
            )

            # Get current configuration
            current_config = await self.mcp_server.get_active_provider_config()
            current_provider = current_config.get("provider")

            # Determine which provider(s) to reset
            if specified_provider == "all":
                providers = await self.mcp_server.get_available_providers()
                reset_all = True
            else:
                providers = [specified_provider or current_provider]
                reset_all = False

            # Collect current vs default values for all affected providers
            reset_details = {}
            for provider in providers:
                try:
                    constraints = await self.mcp_server.get_parameter_constraints(provider)

                    # Determine which parameters to reset
                    if specific_params:
                        # Only reset specified parameters
                        params_to_reset = {
                            k: v for k, v in constraints.items() if k in specific_params
                        }
                    else:
                        # Reset all parameters
                        params_to_reset = constraints

                    # Collect current vs default for each parameter
                    changes = {}
                    for param_name, info in params_to_reset.items():
                        current_value = info["current_value"]
                        default_value = info["default"]

                        if current_value != default_value:
                            changes[param_name] = {
                                "current": current_value,
                                "default": default_value,
                                "will_change": True,
                            }
                        else:
                            changes[param_name] = {
                                "current": current_value,
                                "default": default_value,
                                "will_change": False,
                            }

                    reset_details[provider] = changes

                except Exception as e:
                    logger.warning(
                        event="reset_config_provider_error",
                        provider=provider,
                        error=str(e),
                    )
                    reset_details[provider] = {"error": str(e)}

            # Check if any changes will be made
            any_changes = any(
                any(param["will_change"] for param in changes.values())
                for changes in reset_details.values()
                if isinstance(changes, dict) and "error" not in changes
            )

            if not any_changes:
                return {
                    "status": "no_change",
                    "message": "All parameters are already at their default values",
                    "tool": "reset_config",
                }

            # If not confirmed, return confirmation request
            if not confirmed:
                lines = [
                    "🔄 Configuration Reset Request",
                    "=" * 50,
                    "",
                ]

                if reset_all:
                    lines.append("⚠️  This will reset ALL providers to default settings!")
                    lines.append("")

                for provider, changes in reset_details.items():
                    if "error" in changes:
                        lines.append(f"❌ {provider}: {changes['error']}")
                    else:
                        lines.append(f"📦 {provider.upper()}:")

                        has_changes = False
                        for param_name, info in changes.items():
                            if info["will_change"]:
                                has_changes = True
                                lines.append(
                                    f"  • {param_name}: {info['current']} → {info['default']}"
                                )

                        if not has_changes:
                            lines.append("  (no changes needed)")

                    lines.append("")

                lines.append(
                    "To confirm, use: reset_config("
                    + (f"provider='{specified_provider}', " if specified_provider else "")
                    + "confirm=true)"
                )

                return {
                    "status": "confirmation_required",
                    "message": "\n".join(lines),
                    "reset_details": reset_details,
                    "tool": "reset_config",
                }

            # Execute the reset
            success_count = 0
            error_count = 0
            results = {}

            for provider, changes in reset_details.items():
                if "error" not in changes:
                    try:
                        # Only reset parameters that need changing
                        params_to_reset = {
                            param: info["default"]
                            for param, info in changes.items()
                            if info["will_change"]
                        }

                        if params_to_reset:
                            # Reset to defaults using MCP server method
                            if specific_params:
                                # Reset specific parameters
                                for param_name, default_value in params_to_reset.items():
                                    success = await self.mcp_server.set_provider_parameter(
                                        provider, param_name, default_value
                                    )
                                    if success:
                                        success_count += 1
                            else:
                                # Reset all parameters
                                success = await self.mcp_server.reset_to_defaults(provider)
                                if success:
                                    success_count += 1

                            results[provider] = "success"
                        else:
                            results[provider] = "no_changes"

                    except Exception as e:
                        error_count += 1
                        results[provider] = f"error: {str(e)}"
                        logger.error(
                            event="reset_execution_error",
                            provider=provider,
                            error=str(e),
                        )

            # Build result message
            if error_count == 0:
                result_lines = [
                    "✅ Configuration reset successfully!",
                    "",
                ]

                for provider, result in results.items():
                    if result == "success":
                        result_lines.append(f"✓ {provider}: Reset to defaults")
                    elif result == "no_changes":
                        result_lines.append(f"- {provider}: Already at defaults")

                result_lines.append("")
                result_lines.append(
                    "All affected parameters have been reset to their default values."
                )

                status = "success"
            else:
                result_lines = [
                    "⚠️  Configuration reset completed with errors",
                    "",
                ]

                for provider, result in results.items():
                    if result == "success":
                        result_lines.append(f"✓ {provider}: Reset to defaults")
                    elif result.startswith("error"):
                        result_lines.append(f"❌ {provider}: {result}")

                status = "partial_success"

            result = {
                "status": status,
                "message": "\n".join(result_lines),
                "providers_reset": success_count,
                "errors": error_count,
                "details": results,
                "tool": "reset_config",
            }

            logger.info(
                event="config_reset_completed",
                providers_reset=success_count,
                errors=error_count,
                reset_all=reset_all,
            )

            return result

        except Exception as e:
            logger.error(
                event="reset_config_tool_error",
                error=str(e),
                provider=arguments.get("provider"),
            )

            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to reset configuration: {str(e)}",
                "tool": "reset_config",
            }
