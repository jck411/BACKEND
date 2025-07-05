"""
Shared data models for the backend project.

Following PROJECT_RULES.md:
- Single responsibility per file
- Pydantic models for data validation
- Type hints throughout
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    """Type of data chunk being streamed."""
    TEXT = "text"
    IMAGE = "image"
    ERROR = "error"
    METADATA = "metadata"


class Chunk(BaseModel):
    """
    Data chunk for streaming between components.
    
    Used for WebSocket communication between client and gateway,
    and internal communication between components.
    """
    type: ChunkType
    data: Union[str, bytes]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence_id: Optional[str] = None


class WebSocketMessage(BaseModel):
    """
    WebSocket message format for client-gateway communication.
    """
    action: str = Field(..., description="Action type: 'chat', 'generate_image', 'device_control'")
    payload: Dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(..., description="Unique request identifier")
    user_id: Optional[str] = None


class WebSocketResponse(BaseModel):
    """
    WebSocket response format from gateway to client.
    """
    request_id: str
    status: str = Field(..., description="Status: 'processing', 'chunk', 'complete', 'error'")
    chunk: Optional[Chunk] = None
    error: Optional[str] = None
