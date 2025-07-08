"""
Get Parameter Info Tool for MCP

This tool provides detailed information about AI parameters
through the standard MCP tool interface.

Standard MCP Tool: get_parameter_info
- Shows parameter constraints and valid ranges
- Provides descriptions and defaults
- Indicates current values
- Shows provider-specific differences
"""

from typing import Dict, Any

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from common.logging import get_logger

logger = get_logger(__name__)


class ParameterInfoTool(ToolHandler):
    """
    Standard MCP tool for getting AI parameter information.

    Provides detailed information about parameter constraints,
    valid ranges, and provider-specific differences.
    """

    def __init__(self, mcp_server):
        """Initialize the parameter info tool."""
        self.mcp_server = mcp_server
        logger.info(event="parameter_info_tool_initialized")

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="get_parameter_info",
            description="Get detailed information about AI configuration parameters including valid ranges, constraints, and provider-specific differences.",
            parameters=[
                ToolParameter(
                    name="parameter",
                    type=ToolParameterType.STRING,
                    description="Specific parameter to get info about (e.g., 'temperature', 'max_tokens'). Leave empty for all parameters.",
                    required=False,
                ),
                ToolParameter(
                    name="provider",
                    type=ToolParameterType.STRING,
                    description="Provider to get parameter info for. Uses current provider if not specified.",
                    required=False,
                    enum=["openai", "anthropic", "gemini", "openrouter"],
                ),
                ToolParameter(
                    name="compare",
                    type=ToolParameterType.BOOLEAN,
                    description="Compare parameter constraints across all providers",
                    required=False,
                    default=False,
                ),
            ],
            examples=[
                "get_parameter_info(parameter='temperature')",
                "get_parameter_info(provider='anthropic')",
                "get_parameter_info(parameter='max_tokens', compare=true)",
                "get_parameter_info()",
            ],
            category="ai_configuration",
            version="1.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the get parameter info tool.

        Args:
            arguments: Tool arguments containing optional 'parameter', 'provider', and 'compare'

        Returns:
            Detailed parameter information
        """
        try:
            param_name = arguments.get("parameter")
            specified_provider = arguments.get("provider")
            compare_providers = arguments.get("compare", False)

            logger.info(
                event="parameter_info_tool_executed",
                parameter=param_name,
                provider=specified_provider,
                compare=compare_providers,
            )

            # Get current configuration to determine default provider
            current_config = await self.mcp_server.get_active_provider_config()
            current_provider = current_config.get("provider")

            # Determine which provider(s) to get info for
            if compare_providers:
                providers = await self.mcp_server.get_available_providers()
            else:
                providers = [specified_provider or current_provider]

            # Collect parameter info for each provider
            all_info = {}
            for provider in providers:
                try:
                    constraints = await self.mcp_server.get_parameter_constraints(provider)

                    if param_name:
                        # Filter to specific parameter
                        if param_name in constraints:
                            all_info[provider] = {param_name: constraints[param_name]}
                        else:
                            # Parameter not found for this provider
                            all_info[provider] = {}
                    else:
                        # All parameters
                        all_info[provider] = constraints
                except Exception as e:
                    logger.warning(
                        event="parameter_info_provider_error",
                        provider=provider,
                        error=str(e),
                    )
                    all_info[provider] = {"error": str(e)}

            # Format output
            if param_name and not compare_providers:
                # Single parameter, single provider
                provider = providers[0]
                if provider in all_info and param_name in all_info[provider]:
                    param_info = all_info[provider][param_name]

                    lines = [
                        f"📊 Parameter: {param_name}",
                        "=" * 50,
                        f"Provider: {provider}",
                        "",
                        f"Description: {param_info['description']}",
                        f"Type: {param_info['type']}",
                        f"Current Value: {param_info['current_value']}",
                        f"Default: {param_info['default']}",
                    ]

                    if param_info["min_value"] is not None or param_info["max_value"] is not None:
                        lines.append(
                            f"Range: {param_info['min_value']} - {param_info['max_value']}"
                        )

                    if param_info["enum_values"]:
                        lines.append(f"Valid Options: {', '.join(param_info['enum_values'])}")

                    if param_info["required"]:
                        lines.append("Required: Yes")

                    lines.append("")
                    lines.append("💡 Use 'ai_configure' to modify this parameter")

                    formatted_output = "\n".join(lines)
                else:
                    formatted_output = (
                        f"Parameter '{param_name}' not found for provider '{provider}'"
                    )

            elif compare_providers:
                # Compare across providers
                lines = [
                    f"📊 Parameter Comparison: {param_name or 'All Parameters'}",
                    "=" * 50,
                    "",
                ]

                if param_name:
                    # Compare single parameter across providers
                    for provider, info in all_info.items():
                        if "error" in info:
                            lines.append(f"{provider}: Error - {info['error']}")
                        elif param_name in info:
                            param_info = info[param_name]
                            lines.append(f"📦 {provider.upper()}:")
                            lines.append(
                                f"  Range: {param_info['min_value']} - {param_info['max_value']}"
                            )
                            lines.append(f"  Default: {param_info['default']}")
                            lines.append(f"  Current: {param_info['current_value']}")
                        else:
                            lines.append(f"{provider}: Parameter not available")
                        lines.append("")
                else:
                    # Compare all parameters
                    # First collect all unique parameters
                    all_params = set()
                    for info in all_info.values():
                        if isinstance(info, dict) and "error" not in info:
                            all_params.update(info.keys())

                    for param in sorted(all_params):
                        lines.append(f"• {param}:")
                        for provider, info in all_info.items():
                            if "error" not in info and param in info:
                                param_info = info[param]
                                lines.append(
                                    f"  {provider}: {param_info['min_value']} - {param_info['max_value']} (default: {param_info['default']})"
                                )
                        lines.append("")

                formatted_output = "\n".join(lines)

            else:
                # All parameters for single provider
                provider = providers[0]
                info = all_info[provider]

                if "error" in info:
                    formatted_output = f"Error getting parameters for {provider}: {info['error']}"
                else:
                    lines = [
                        f"📊 All Parameters for {provider.upper()}",
                        "=" * 50,
                        "",
                    ]

                    for param_name, param_info in info.items():
                        lines.append(f"• {param_name}:")
                        lines.append(f"  Description: {param_info['description']}")
                        lines.append(f"  Type: {param_info['type']}")
                        lines.append(
                            f"  Current: {param_info['current_value']} {'(default)' if param_info['current_value'] == param_info['default'] else '(modified)'}"
                        )

                        if (
                            param_info["min_value"] is not None
                            or param_info["max_value"] is not None
                        ):
                            lines.append(
                                f"  Range: {param_info['min_value']} - {param_info['max_value']}"
                            )

                        if param_info["enum_values"]:
                            lines.append(f"  Options: {', '.join(param_info['enum_values'])}")

                        lines.append("")

                    lines.append("💡 Use 'ai_configure' to modify these parameters")

                    formatted_output = "\n".join(lines)

            result = {
                "status": "success",
                "parameter_info": formatted_output,
                "message": "Parameter information retrieved successfully",
                "tool": "get_parameter_info",
            }

            logger.info(
                event="parameter_info_completed",
                parameter=param_name,
                providers_count=len(providers),
                compare=compare_providers,
            )

            return result

        except Exception as e:
            logger.error(
                event="parameter_info_tool_error",
                error=str(e),
                parameter=arguments.get("parameter"),
            )

            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to get parameter info: {str(e)}",
                "tool": "get_parameter_info",
            }
