"""
Standard I/O Transport for MCP

Implements stdio transport as required by MCP 2025 specification for local tool execution.
This enables MCP clients to spawn our server as a subprocess and communicate via stdin/stdout.

Reference: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from common.logging import get_logger
from ..jsonrpc import (
    JSONRPCHandler,
    JSONRPCRequest,
    JSONRPCNotification,
    PARSE_ERROR,
    INTERNAL_ERROR,
)
from ..mcp2025_server import MCP2025Server

logger = get_logger(__name__)


class StdioTransport:
    """
    Standard I/O transport for MCP communication.

    Enables MCP clients to communicate with our server via stdin/stdout,
    which is the standard method for local tool execution in MCP.
    """

    def __init__(self, mcp_server: MCP2025Server):
        """Initialize stdio transport."""
        self.mcp_server = mcp_server
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stdio")
        self.running = False
        self.reader_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the stdio transport."""
        if self.running:
            return

        self.running = True
        logger.info(event="stdio_transport_started", message="MCP stdio transport started")

        # Start reading from stdin
        self.reader_task = asyncio.create_task(self._read_stdin())

        # Send initial log to stderr for debugging
        await self._log_to_stderr("MCP server ready on stdio")

    async def stop(self) -> None:
        """Stop the stdio transport."""
        if not self.running:
            return

        self.running = False

        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass

        self.executor.shutdown(wait=True)
        logger.info(event="stdio_transport_stopped")

    async def _read_stdin(self) -> None:
        """Read JSON-RPC messages from stdin."""
        loop = asyncio.get_event_loop()

        try:
            while self.running:
                # Read a line from stdin asynchronously
                line = await loop.run_in_executor(self.executor, sys.stdin.readline)

                if not line:  # EOF
                    await self._log_to_stderr("Received EOF, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                await self._handle_message(line)

        except Exception as e:
            logger.error(event="stdin_read_error", error=str(e))
            await self._log_to_stderr(f"Error reading stdin: {e}")

    async def _handle_message(self, message: str) -> None:
        """Handle a JSON-RPC message from stdin."""
        try:
            # Parse JSON
            data = json.loads(message)

            # Parse as JSON-RPC message
            rpc_message = JSONRPCHandler.parse_message(data)

            if isinstance(rpc_message, JSONRPCRequest):
                # Handle request and send response to stdout
                response = await self.mcp_server._handle_request(rpc_message)
                if response:
                    await self._write_stdout(response.model_dump())

            elif isinstance(rpc_message, JSONRPCNotification):
                # Handle notification (no response)
                await self.mcp_server._handle_notification(rpc_message)

            else:
                # Unexpected message type
                await self._log_to_stderr(f"Unexpected message type: {type(rpc_message)}")

        except json.JSONDecodeError as e:
            # Send parse error
            error_response = JSONRPCHandler.create_error_response(
                None, PARSE_ERROR, f"Parse error: {str(e)}"
            )
            await self._write_stdout(error_response.model_dump())

        except Exception as e:
            logger.error(event="message_handle_error", error=str(e))
            # Send internal error
            error_response = JSONRPCHandler.create_error_response(
                None, INTERNAL_ERROR, f"Internal error: {str(e)}"
            )
            await self._write_stdout(error_response.model_dump())

    async def _write_stdout(self, data: Dict[str, Any]) -> None:
        """Write JSON-RPC response to stdout."""
        try:
            message = json.dumps(data, separators=(",", ":"))

            # Write to stdout in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, lambda: print(message, flush=True))

        except Exception as e:
            logger.error(event="stdout_write_error", error=str(e))
            await self._log_to_stderr(f"Error writing to stdout: {e}")

    async def _log_to_stderr(self, message: str) -> None:
        """Log a message to stderr for debugging."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor, lambda: print(f"[MCP] {message}", file=sys.stderr, flush=True)
            )
        except Exception:
            # Ignore stderr logging errors
            pass

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a notification to the client."""
        notification = JSONRPCHandler.create_notification(method, params)
        await self._write_stdout(notification.model_dump())


class StdioServer:
    """
    Standalone stdio MCP server.

    Can be run as a standalone executable for stdio transport.
    """

    def __init__(self):
        """Initialize stdio server."""
        self.mcp_server = MCP2025Server()
        self.transport = StdioTransport(self.mcp_server)

    async def run(self) -> None:
        """Run the stdio server."""
        try:
            await self.transport.start()

            # Keep running until EOF or error
            while self.transport.running:
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            await self.transport._log_to_stderr("Received interrupt, shutting down")
        except Exception as e:
            await self.transport._log_to_stderr(f"Server error: {e}")
        finally:
            await self.transport.stop()


async def main() -> None:
    """Main entry point for stdio server."""
    server = StdioServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
