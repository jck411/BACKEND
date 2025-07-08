"""
Base adapter interface for AI providers.

Following PROJECT_RULES.md:
- Single responsibility: Define adapter interface
- Type safety with Pydantic models
- Async design for I/O operations
- MCP integration for dynamic configuration
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.mcp2025_server import MCP2025Server


class AdapterRequest(BaseModel):
    """Request to an AI adapter."""

    messages: List[Dict[str, Any]] = Field(description="Chat messages")
    system_prompt: Optional[str] = Field(default=None, description="System prompt override")
    temperature: Optional[float] = Field(default=None, description="Temperature override")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens override")
    # MCP integration: tools managed by MCP service
    mcp_tools: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="MCP-provided tools"
    )


class AdapterResponse(BaseModel):
    """Response from an AI adapter."""

    content: Optional[str] = Field(default=None, description="Generated content")
    finish_reason: Optional[str] = Field(default=None, description="Completion reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    # MCP integration: tool calls handled via MCP
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="MCP tool calls")


class BaseAdapter(ABC):
    """Base class for AI provider adapters."""

    def __init__(self, mcp_server: Optional["MCP2025Server"] = None):
        """
        Initialize adapter with MCP server.

        Args:
            mcp_server: MCP 2025 server instance for dynamic configuration.
                       If None, adapter will fail on first use (fail-fast).
        """
        self.mcp_server = mcp_server
        if not self.mcp_server:
            # Log warning but don't fail yet - fail on first use
            import logging

            logging.warning("Adapter initialized without MCP server - will fail on first use")

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Capability probe - does this adapter support function calling?"""
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Capability probe - does this adapter support streaming?"""
        pass

    @abstractmethod
    def translate_tools(self, mcp_tools: List[Dict[str, Any]]) -> Any:
        """
        Schema transformer - convert MCP tools to provider-specific format.
        Pure transformation, stateless, side-effect-free.
        """
        pass

    @abstractmethod
    async def chat_completion(
        self, request: AdapterRequest
    ) -> AsyncGenerator[AdapterResponse, None]:
        """Generate streaming chat completions."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the adapter is healthy."""
        pass

    # Image generation will be moved to separate specialized adapters in the future
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate an image (optional capability)."""
        raise NotImplementedError("Image generation not supported by this adapter")
