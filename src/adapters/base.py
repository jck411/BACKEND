"""
Base adapter interface for AI providers.

Following PROJECT_RULES.md:
- Single responsibility: Define adapter interface
- Type safety with Pydantic models
- Async design for I/O operations
- Future-ready for MCP integration
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel, Field


class AdapterRequest(BaseModel):
    """Request to an AI adapter."""

    messages: List[Dict[str, Any]] = Field(description="Chat messages")
    system_prompt: Optional[str] = Field(default=None, description="System prompt override")
    temperature: Optional[float] = Field(default=None, description="Temperature override")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens override")
    # Future MCP integration: tools and context will be managed by MCP service
    # tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="MCP-provided tools")


class AdapterResponse(BaseModel):
    """Response from an AI adapter."""

    content: Optional[str] = Field(default=None, description="Generated content")
    finish_reason: Optional[str] = Field(default=None, description="Completion reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    # Future MCP integration: tool calls will be handled via MCP
    # tool_calls: List[ToolCall] = Field(default_factory=list, description="MCP tool calls")


class BaseAdapter(ABC):
    """Base class for AI provider adapters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize adapter with configuration."""
        self.config = config

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
