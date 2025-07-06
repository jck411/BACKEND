"""
Media handling for WebSocket connections.

Handles binary data, media streaming, and format validation.
Following PROJECT_RULES.md:
- Single responsibility: media processing only
- Async I/O for all operations
- Proper error handling with timeouts
"""

from typing import Dict, Any, Optional
import asyncio

from common.logging import get_logger
from common.models import WebSocketResponse, Chunk, ChunkType

logger = get_logger(__name__)


class MediaHandler:
    """Handles media processing and streaming for WebSocket connections."""

    def __init__(self, max_file_size: int = 50 * 1024 * 1024):  # 50MB default
        self.max_file_size = max_file_size
        self.supported_image_types = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        self.supported_audio_types = {".mp3", ".wav", ".ogg", ".m4a"}
        self.supported_video_types = {".mp4", ".webm", ".mov"}

    async def validate_media_upload(
        self, media_data: bytes, content_type: str, filename: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate uploaded media data.

        Returns:
            (is_valid, error_message)
        """
        try:
            # Check file size
            if len(media_data) > self.max_file_size:
                return False, f"File size {len(media_data)} exceeds limit {self.max_file_size}"

            # Basic content type validation
            if not self._is_supported_media_type(content_type):
                return False, f"Unsupported media type: {content_type}"

            logger.info(
                event="media_validated",
                message="Media upload validated successfully",
                content_type=content_type,
                size=len(media_data),
                filename=filename,
            )

            return True, None

        except Exception as e:
            logger.error(
                event="media_validation_failed",
                message="Media validation failed",
                error=str(e),
                content_type=content_type,
            )
            return False, f"Validation error: {str(e)}"

    async def process_media_chunk(
        self, chunk_data: bytes, chunk_index: int, total_chunks: int, media_type: str
    ) -> WebSocketResponse:
        """
        Process a media chunk for streaming.

        Args:
            chunk_data: Binary chunk data
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
            media_type: Type of media being processed

        Returns:
            WebSocketResponse with processed chunk
        """
        try:
            # Future: Add media-specific processing here
            # - Image resizing/compression
            # - Audio format conversion
            # - Video frame extraction

            is_final = chunk_index == total_chunks - 1

            chunk = Chunk(
                type=ChunkType.BINARY,
                data=chunk_data,
                metadata={
                    "chunk_index": chunk_index,
                    "total_chunks": total_chunks,
                    "media_type": media_type,
                    "is_final": is_final,
                },
            )

            logger.info(
                event="media_chunk_processed",
                message="Media chunk processed",
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                media_type=media_type,
                size=len(chunk_data),
            )

            return WebSocketResponse(
                request_id=f"media_chunk_{chunk_index}",
                status="streaming" if not is_final else "complete",
                chunk=chunk,
            )

        except Exception as e:
            logger.error(
                event="media_chunk_processing_failed",
                message="Media chunk processing failed",
                error=str(e),
                chunk_index=chunk_index,
                media_type=media_type,
            )
            raise

    def _is_supported_media_type(self, content_type: str) -> bool:
        """Check if the content type is supported."""
        return any(
            content_type.startswith(prefix)
            for prefix in ["image/", "audio/", "video/", "application/"]
        )

    async def get_media_info(self, media_data: bytes, content_type: str) -> Dict[str, Any]:
        """
        Extract metadata from media data.

        Returns:
            Dictionary with media information
        """
        try:
            # Future: Add actual media analysis
            # - Image dimensions
            # - Audio duration/bitrate
            # - Video resolution/fps

            info = {
                "size": len(media_data),
                "content_type": content_type,
                "timestamp": asyncio.get_event_loop().time(),
            }

            if content_type.startswith("image/"):
                info.update({"type": "image", "format": content_type.split("/")[1]})
            elif content_type.startswith("audio/"):
                info.update({"type": "audio", "format": content_type.split("/")[1]})
            elif content_type.startswith("video/"):
                info.update({"type": "video", "format": content_type.split("/")[1]})

            return info

        except Exception as e:
            logger.error(
                event="media_info_extraction_failed",
                message="Failed to extract media info",
                error=str(e),
                content_type=content_type,
            )
            return {"size": len(media_data), "content_type": content_type, "error": str(e)}
