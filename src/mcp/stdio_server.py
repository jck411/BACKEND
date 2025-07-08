#!/usr/bin/env python3
"""
MCP 2025 Stdio Server

A standalone script that provides MCP server functionality over stdio transport.
This enables MCP clients to spawn our server as a subprocess for local tool execution.

Usage:
    python -m src.mcp.stdio_server

Or directly:
    python src/mcp/stdio_server.py

The server will read JSON-RPC messages from stdin and write responses to stdout.
This follows the MCP 2025 specification for local tool execution.
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path for proper imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))


async def main() -> None:
    """Main entry point for stdio server."""
    # Import here to avoid issues with path setup
    from mcp.transports.stdio import StdioServer

    try:
        server = StdioServer()
        await server.run()
    except KeyboardInterrupt:
        print("[MCP] Received interrupt, shutting down", file=sys.stderr)
    except Exception as e:
        print(f"[MCP] Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
