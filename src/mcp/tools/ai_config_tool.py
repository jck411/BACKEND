"""
AI Configuration Tool for MCP

This tool provides natural language configuration of AI model parameters
through the standard MCP tool interface.

The LLM itself handles the interpretation of natural language commands
and translates them to appropriate configuration changes.
"""

from typing import Dict, Any, TYPE_CHECKING

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from common.logging import get_logger

if TYPE_CHECKING:
    from ..mcp2025_server import MCP2025Server

logger = get_logger(__name__)


class AIConfigurationTool(ToolHandler):
    """
    Standard MCP tool for AI parameter configuration.

    This is a simple tool that lets the LLM interpret natural language
    configuration requests and apply changes directly.
    """

    def __init__(self, mcp_server: "MCP2025Server"):
        """Initialize the AI configuration tool."""
        self.mcp_server = mcp_server

        logger.info(
            event="ai_config_tool_initialized",
            supported_providers=["openai", "anthropic", "gemini", "openrouter"],
        )

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="ai_configure",
            description="Configure AI model parameters. The LLM will interpret your request and apply appropriate changes.",
            parameters=[
                ToolParameter(
                    name="provider",
                    type=ToolParameterType.STRING,
                    description="Target provider (openai, anthropic, gemini, openrouter). If not specified, applies to current provider.",
                    required=False,
                ),
                ToolParameter(
                    name="parameter",
                    type=ToolParameterType.STRING,
                    description="Parameter to change (temperature, max_tokens, system_prompt, model)",
                    required=True,
                ),
                ToolParameter(
                    name="value",
                    type=ToolParameterType.STRING,
                    description="New value for the parameter. Can be a number, string, or special value like 'default'",
                    required=True,
                ),
            ],
            examples=[
                "ai_configure(parameter='temperature', value='0.9')",
                "ai_configure(parameter='temperature', value='default')",
                "ai_configure(provider='anthropic', parameter='model', value='claude-3-opus-20240229')",
                "ai_configure(parameter='system_prompt', value='You are a creative writing assistant')",
            ],
            category="ai_configuration",
            version="2.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the AI configuration tool.

        The LLM has already interpreted the user's natural language request
        and converted it to specific parameter changes.

        Args:
            arguments: Tool arguments with provider, parameter, and value

        Returns:
            Configuration result with applied changes
        """
        try:
            # Get arguments
            provider = arguments.get("provider")
            parameter = arguments["parameter"]
            value_str = arguments["value"]

            # Get current configuration
            current_config = await self.mcp_server.get_active_provider_config()
            current_provider = current_config.get("provider", "openai")

            # Use current provider if not specified
            if not provider:
                provider = current_provider

            # Handle special values
            if value_str.lower() == "default":
                # Get default value for this parameter
                constraints = await self.mcp_server.get_parameter_constraints(provider)
                if parameter in constraints:
                    value = constraints[parameter]["default"]
                else:
                    return {
                        "message": f"Unknown parameter '{parameter}' for provider '{provider}'",
                        "status": "error",
                    }
            else:
                # Parse value based on parameter type
                constraints = await self.mcp_server.get_parameter_constraints(provider)
                if parameter in constraints:
                    param_type = constraints[parameter]["type"]
                    if param_type == "number":
                        try:
                            value = float(value_str)
                        except ValueError:
                            return {
                                "message": f"Parameter '{parameter}' requires a numeric value, got '{value_str}'",
                                "status": "error",
                            }
                    elif param_type == "integer":
                        try:
                            value = int(value_str)
                        except ValueError:
                            return {
                                "message": f"Parameter '{parameter}' requires an integer value, got '{value_str}'",
                                "status": "error",
                            }
                    else:
                        value = value_str
                else:
                    # Special handling for model parameter
                    if parameter == "model":
                        value = value_str
                    else:
                        return {
                            "message": f"Unknown parameter '{parameter}' for provider '{provider}'",
                            "status": "error",
                        }

            # Apply the change
            if parameter == "model":
                # Special handling for model changes
                models_info = await self.mcp_server.get_available_models(provider)
                model_names = [m["name"] for m in models_info["models"]]
                if value not in model_names:
                    return {
                        "message": f"Model '{value}' not available for {provider}. Available models: {', '.join(model_names)}",
                        "status": "error",
                    }

                # Update model
                success = await self.mcp_server.set_provider_parameter(provider, "model", value)
            else:
                # Update parameter
                success = await self.mcp_server.set_provider_parameter(provider, parameter, value)

            if success:
                # Get updated configuration
                updated_config = await self.mcp_server.get_active_provider_config()

                return {
                    "message": f"Successfully updated {parameter} to {value} for {provider}",
                    "status": "success",
                    "provider": provider,
                    "parameter": parameter,
                    "old_value": current_config.get(parameter),
                    "new_value": value,
                    "current_config": updated_config,
                }
            else:
                return {
                    "message": f"Failed to update {parameter} for {provider}",
                    "status": "error",
                }

        except Exception as e:
            logger.error(
                event="ai_config_tool_error",
                error=str(e),
                arguments=arguments,
            )

            return {
                "status": "error",
                "message": f"Configuration error: {str(e)}",
            }
