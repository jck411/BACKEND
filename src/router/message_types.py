"""
Internal message types for router communication.

Added 2025-07-05: Router component message types.
Following PROJECT_RULES.md: Single responsibility, type-safe models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """Types of requests the router can handle."""

    CHAT = "chat"  # Text generation with LLM function calling for device control
    IMAGE_GENERATION = "generate_image"  # Image generation requests
    AUDIO_STREAM = "audio_stream"  # TTS and audio generation
    FRONTEND_COMMAND = "frontend_command"  # UI updates and notifications
    MCP_REQUEST = "mcp_request"  # Model Context Protocol requests for self-configuration


class RouterRequest(BaseModel):
    """Internal request format for router processing."""

    request_id: str
    request_type: RequestType
    payload: Dict[str, Any]
    user_id: Optional[str] = None
    connection_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RouterResponse(BaseModel):
    """Internal response format from router."""

    request_id: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
