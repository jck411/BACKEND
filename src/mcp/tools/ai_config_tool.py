"""
AI Configuration Tool for MCP

This tool provides natural language configuration of AI model parameters
through the standard MCP tool interface.

Standard MCP Tool: ai_configure
- Natural language parameter adjustment
- Provider-agnostic parameter mapping
- Confidence-based decision making
- Real-time configuration updates
"""

from typing import Dict, Any, List

from ..tool_registry import ToolHandler, Tool, ToolParameter, ToolParameterType
from ..self_config_service import MCPSelfConfigService
from common.runtime_config import RuntimeConfigManager
from common.logging import get_logger

logger = get_logger(__name__)


class AIConfigurationTool(ToolHandler):
    """
    Standard MCP tool for AI parameter configuration.

    Provides natural language interface for adjusting AI model parameters
    across any provider (OpenAI, Anthropic, Gemini, etc.).
    """

    def __init__(self, runtime_config_manager: RuntimeConfigManager):
        """Initialize the AI configuration tool."""
        self.runtime_config_manager = runtime_config_manager
        self.self_config_service = MCPSelfConfigService(runtime_config_manager)

        logger.info(
            event="ai_config_tool_initialized",
            supported_providers=["openai", "anthropic", "gemini", "openrouter"],
        )

    def get_tool_definition(self) -> Tool:
        """Get the standard MCP tool definition."""
        return Tool(
            name="ai_configure",
            description="Configure AI model parameters using natural language commands. Supports creative/conservative adjustments, explicit parameter setting, and provider-aware constraints.",
            parameters=[
                ToolParameter(
                    name="request",
                    type=ToolParameterType.STRING,
                    description="Natural language description of desired parameter changes. Examples: 'make responses more creative', 'set temperature to 0.8', 'reduce randomness and be more focused'",
                    required=True,
                ),
                ToolParameter(
                    name="context",
                    type=ToolParameterType.OBJECT,
                    description="Additional context for the configuration request",
                    required=False,
                    properties={
                        "user_preference": ToolParameter(
                            name="user_preference",
                            type=ToolParameterType.STRING,
                            description="User's preferred style (creative, balanced, focused)",
                        ),
                        "current_task": ToolParameter(
                            name="current_task",
                            type=ToolParameterType.STRING,
                            description="Current task context for parameter optimization",
                        ),
                    },
                ),
                ToolParameter(
                    name="confidence_threshold",
                    type=ToolParameterType.NUMBER,
                    description="Minimum confidence required to apply changes automatically (0.0-1.0)",
                    required=False,
                    default=0.8,
                    minimum=0.0,
                    maximum=1.0,
                ),
            ],
            examples=[
                "ai_configure(request='make responses more creative and colorful')",
                "ai_configure(request='set temperature to 0.9')",
                "ai_configure(request='reduce randomness and be more focused')",
                "ai_configure(request='make responses shorter and more concise')",
                "ai_configure(request='reset all parameters to default values')",
                "ai_configure(request='turn up creativity to maximum', context={'user_preference': 'creative'})",
            ],
            category="ai_configuration",
            version="1.0.0",
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the AI configuration tool.

        Args:
            arguments: Tool arguments containing 'request' and optional 'context'

        Returns:
            Configuration result with applied changes and explanations
        """
        try:
            request = arguments["request"]
            context = arguments.get("context", {})
            confidence_threshold = arguments.get("confidence_threshold", 0.8)

            logger.info(
                event="ai_config_tool_executed",
                request=request[:100],  # Log first 100 chars
                context_keys=list(context.keys()),
                confidence_threshold=confidence_threshold,
            )

            # Execute natural language adjustment through self-config service
            result = await self.self_config_service.execute_natural_language_adjustment(
                request, context
            )

            # Add tool-specific metadata
            tool_result = {
                **result,
                "tool": "ai_configure",
                "provider_info": await self._get_provider_info(),
                "usage_examples": self._get_usage_examples(result.get("status")),
            }

            # Log the result
            logger.info(
                event="ai_config_applied",
                status=result.get("status"),
                confidence=result.get("confidence"),
                adjustments=result.get("adjustments", {}),
                provider=tool_result["provider_info"]["active_provider"],
            )

            return tool_result

        except Exception as e:
            logger.error(
                event="ai_config_tool_error",
                error=str(e),
                request=arguments.get("request", "unknown"),
            )

            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to configure AI parameters: {str(e)}",
                "tool": "ai_configure",
            }

    async def _get_provider_info(self) -> Dict[str, Any]:
        """Get current provider information."""
        try:
            config = self.runtime_config_manager.get_active_provider_config()

            return {
                "active_provider": config["provider"],
                "model": config["model"],
                "current_parameters": {
                    k: v for k, v in config.items() if k not in ["provider", "model"]
                },
            }
        except Exception as e:
            logger.warning(event="provider_info_error", error=str(e))
            return {"active_provider": "unknown", "model": "unknown", "current_parameters": {}}

    def _get_usage_examples(self, status: str) -> List[str]:
        """Get relevant usage examples based on execution status."""
        base_examples = [
            "Make responses more creative and detailed",
            "Reduce randomness and be more focused",
            "Set temperature to 0.8",
            "Make responses shorter and more concise",
            "Reset to default settings",
        ]

        if status == "no_changes":
            return [
                "Try being more specific: 'increase creativity'",
                "Use explicit values: 'set temperature to 0.9'",
                "Describe the style you want: 'make responses more colorful'",
            ]
        elif status == "applied_with_explanation":
            return [
                "You can be more explicit if needed",
                "Ask questions if the changes aren't what you expected",
                "Use 'reset to defaults' to start over",
            ]

        return base_examples
