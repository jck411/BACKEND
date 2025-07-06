"""
MCP Connection Manager for Model Context Protocol integration.

This module manages MCP capabilities and provides integration with the
existing request router and WebSocket system.
"""

from typing import Dict, Any
from dataclasses import dataclass

from common.logging import get_logger
from common.runtime_config import RuntimeConfigManager
from .self_config_service import MCPSelfConfigService

logger = get_logger(__name__)


@dataclass
class MCPCapability:
    """Represents an MCP capability."""

    id: str
    name: str
    description: str
    service: Any  # The service that implements this capability
    enabled: bool = True


class MCPConnectionManager:
    """Manages MCP capabilities and their integration with the request router."""

    def __init__(self, runtime_config_manager: RuntimeConfigManager):
        """Initialize the MCP connection manager."""
        self.runtime_config_manager = runtime_config_manager
        self.capabilities: Dict[str, MCPCapability] = {}

        # Initialize built-in capabilities
        self._initialize_capabilities()

        logger.info(event="mcp_manager_initialized", capabilities=list(self.capabilities.keys()))

    def _initialize_capabilities(self) -> None:
        """Initialize built-in MCP capabilities."""

        # Self-configuration capability
        self_config_service = MCPSelfConfigService(self.runtime_config_manager)
        self.capabilities["ai_self_configuration"] = MCPCapability(
            id="ai_self_configuration",
            name="AI Self-Configuration",
            description="Allows AI models to modify their own parameters via natural language",
            service=self_config_service,
        )

        logger.info(event="mcp_capabilities_initialized", count=len(self.capabilities))

    async def discover_capabilities(self) -> Dict[str, Any]:
        """
        Discover all available MCP capabilities.

        Returns:
            Dictionary of capabilities with their details
        """
        capabilities_info = {}

        for capability_id, capability in self.capabilities.items():
            if capability.enabled:
                try:
                    if hasattr(capability.service, "discover_capabilities"):
                        service_info = await capability.service.discover_capabilities()
                        capabilities_info[capability_id] = service_info
                    else:
                        capabilities_info[capability_id] = {
                            "id": capability.id,
                            "name": capability.name,
                            "description": capability.description,
                            "status": "available",
                        }
                except Exception as e:
                    logger.error(
                        event="mcp_capability_discovery_error",
                        capability_id=capability_id,
                        error=str(e),
                    )
                    capabilities_info[capability_id] = {
                        "id": capability.id,
                        "name": capability.name,
                        "description": capability.description,
                        "status": "error",
                        "error": str(e),
                    }

        logger.info(
            event="mcp_capabilities_discovered",
            count=len(capabilities_info),
            enabled_capabilities=list(capabilities_info.keys()),
        )

        return capabilities_info

    async def execute_capability(
        self, capability_id: str, action: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific MCP capability action.

        Args:
            capability_id: ID of the capability to execute
            action: Action to perform
            parameters: Parameters for the action

        Returns:
            Execution result
        """
        if capability_id not in self.capabilities:
            return {
                "status": "error",
                "error": f"Unknown capability: {capability_id}",
                "available_capabilities": list(self.capabilities.keys()),
            }

        capability = self.capabilities[capability_id]

        if not capability.enabled:
            return {"status": "error", "error": f"Capability {capability_id} is disabled"}

        try:
            service = capability.service

            # Route to appropriate service method based on action
            if action == "discover":
                if hasattr(service, "discover_capabilities"):
                    result = await service.discover_capabilities()
                else:
                    result = {
                        "id": capability.id,
                        "name": capability.name,
                        "description": capability.description,
                        "status": "available",
                    }

            elif action == "execute" and capability_id == "ai_self_configuration":
                # Handle self-configuration requests
                natural_request = parameters.get("request", "")
                user_context = parameters.get("context", {})

                if not natural_request:
                    return {
                        "status": "error",
                        "error": "No request provided for self-configuration",
                    }

                result = await service.execute_natural_language_adjustment(
                    natural_request, user_context
                )

            else:
                return {
                    "status": "error",
                    "error": f"Unknown action '{action}' for capability '{capability_id}'",
                }

            logger.info(
                event="mcp_capability_executed",
                capability_id=capability_id,
                action=action,
                status=result.get("status", "unknown"),
            )

            return result

        except Exception as e:
            logger.error(
                event="mcp_capability_execution_error",
                capability_id=capability_id,
                action=action,
                error=str(e),
            )

            return {
                "status": "error",
                "error": f"Failed to execute {capability_id}.{action}: {str(e)}",
            }

    async def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP requests from the WebSocket gateway.

        Args:
            request: MCP request with action and parameters

        Returns:
            MCP response
        """
        try:
            action = request.get("action")
            capability_id = request.get("capability_id")
            parameters = request.get("parameters", {})

            if action == "discover_all":
                # Discover all capabilities
                capabilities = await self.discover_capabilities()
                return {
                    "type": "mcp_response",
                    "action": "discover_all",
                    "status": "success",
                    "capabilities": capabilities,
                }

            elif action == "execute" and capability_id:
                # Execute specific capability
                result = await self.execute_capability(capability_id, "execute", parameters)
                return {
                    "type": "mcp_response",
                    "action": "execute",
                    "capability_id": capability_id,
                    "status": result.get("status", "unknown"),
                    "result": result,
                }

            elif action == "discover" and capability_id:
                # Discover specific capability
                result = await self.execute_capability(capability_id, "discover", parameters)
                return {
                    "type": "mcp_response",
                    "action": "discover",
                    "capability_id": capability_id,
                    "status": "success",
                    "capability": result,
                }

            else:
                return {
                    "type": "mcp_response",
                    "status": "error",
                    "error": "Invalid MCP request format. Expected 'action' and optionally 'capability_id'.",
                }

        except Exception as e:
            logger.error(event="mcp_request_handling_error", error=str(e), request=request)

            return {
                "type": "mcp_response",
                "status": "error",
                "error": f"Failed to handle MCP request: {str(e)}",
            }

    def enable_capability(self, capability_id: str) -> bool:
        """Enable a capability."""
        if capability_id in self.capabilities:
            self.capabilities[capability_id].enabled = True
            logger.info(event="mcp_capability_enabled", capability_id=capability_id)
            return True
        return False

    def disable_capability(self, capability_id: str) -> bool:
        """Disable a capability."""
        if capability_id in self.capabilities:
            self.capabilities[capability_id].enabled = False
            logger.info(event="mcp_capability_disabled", capability_id=capability_id)
            return True
        return False

    def get_capability_status(self) -> Dict[str, Any]:
        """Get status of all capabilities."""
        status = {}
        for capability_id, capability in self.capabilities.items():
            status[capability_id] = {
                "name": capability.name,
                "description": capability.description,
                "enabled": capability.enabled,
            }
        return status
