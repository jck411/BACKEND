"""
Show Current Configuration Tool for MCP

This tool displays the current AI configuration settings
through the standard MCP tool interface.

Standard MCP Tool: show_current_config
- Displays active provider and model
- Shows all current parameter values
- Indicates which parameters differ from defaults
- Provides parameter constraints and valid ranges
"""

from typing import Dict, Any

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from common.logging import get_logger

logger = get_logger(__name__)


class ShowConfigTool(ToolHandler):
    """
    Standard MCP tool for displaying current AI configuration.

    Provides comprehensive view of current settings including
    active provider, model, and all parameter values.
    """

    def __init__(self, mcp_server):
        """Initialize the show config tool."""
        self.mcp_server = mcp_server
        logger.info(event="show_config_tool_initialized")

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="show_current_config",
            description="Display current AI configuration including provider, model, and all parameter settings. Shows which values differ from defaults and provides valid ranges.",
            parameters=[
                ToolParameter(
                    name="verbose",
                    type=ToolParameterType.BOOLEAN,
                    description="Include detailed parameter descriptions and constraints",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="format",
                    type=ToolParameterType.STRING,
                    description="Output format for the configuration",
                    required=False,
                    default="detailed",
                    enum=["detailed", "compact", "json"],
                ),
            ],
            examples=[
                "show_current_config()",
                "show_current_config(verbose=true)",
                "show_current_config(format='compact')",
                "show_current_config(verbose=true, format='json')",
            ],
            category="ai_configuration",
            version="1.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the show current config tool.

        Args:
            arguments: Tool arguments containing optional 'verbose' and 'format'

        Returns:
            Current configuration details
        """
        try:
            verbose = arguments.get("verbose", False)
            output_format = arguments.get("format", "detailed")

            logger.info(
                event="show_config_tool_executed",
                verbose=verbose,
                format=output_format,
            )

            # Get current configuration from MCP server
            config = await self.mcp_server.get_active_provider_config()
            provider = config.get("provider", "unknown")
            model = config.get("model", "unknown")

            # Get parameter constraints for the current provider
            constraints = await self.mcp_server.get_parameter_constraints(provider)

            # Build configuration display
            if output_format == "json":
                # Raw JSON format
                display_data = {
                    "provider": provider,
                    "model": model,
                    "parameters": {},
                    "constraints": constraints if verbose else {},
                }

                for param_name, constraint in constraints.items():
                    display_data["parameters"][param_name] = {
                        "value": constraint["current_value"],
                        "default": constraint["default"],
                        "is_default": constraint["current_value"] == constraint["default"],
                    }

                formatted_output = display_data

            elif output_format == "compact":
                # Compact text format
                lines = [
                    f"Provider: {provider}",
                    f"Model: {model}",
                    "",
                    "Parameters:",
                ]

                for param_name, constraint in constraints.items():
                    value = constraint["current_value"]
                    is_default = value == constraint["default"]
                    status = "" if is_default else " *"
                    lines.append(f"  {param_name}: {value}{status}")

                formatted_output = "\n".join(lines)

            else:  # detailed format
                # Detailed text format
                lines = [
                    "🤖 Current AI Configuration",
                    "=" * 50,
                    f"Provider: {provider}",
                    f"Model: {model}",
                    "",
                    "📊 Parameters:",
                ]

                for param_name, constraint in constraints.items():
                    value = constraint["current_value"]
                    default = constraint["default"]
                    is_default = value == default

                    lines.append(f"\n• {param_name}:")
                    lines.append(
                        f"  Current: {value} {'(default)' if is_default else '(modified)'}"
                    )

                    if verbose:
                        lines.append(f"  Default: {default}")
                        lines.append(f"  Type: {constraint['type']}")

                        if (
                            constraint["min_value"] is not None
                            or constraint["max_value"] is not None
                        ):
                            range_str = (
                                f"  Range: {constraint['min_value']} - {constraint['max_value']}"
                            )
                            lines.append(range_str)

                        if constraint["enum_values"]:
                            lines.append(f"  Options: {', '.join(constraint['enum_values'])}")

                        if constraint["description"]:
                            lines.append(f"  Description: {constraint['description']}")

                lines.append("")
                lines.append("💡 Use 'ai_configure' to modify these settings")

                formatted_output = "\n".join(lines)

            result = {
                "status": "success",
                "provider": provider,
                "model": model,
                "configuration": formatted_output if isinstance(formatted_output, str) else None,
                "data": formatted_output if isinstance(formatted_output, dict) else None,
                "message": f"Showing configuration for {provider} ({model})",
                "tool": "show_current_config",
            }

            logger.info(
                event="show_config_completed",
                provider=provider,
                model=model,
                format=output_format,
            )

            return result

        except Exception as e:
            logger.error(
                event="show_config_tool_error",
                error=str(e),
            )

            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to show configuration: {str(e)}",
                "tool": "show_current_config",
            }
