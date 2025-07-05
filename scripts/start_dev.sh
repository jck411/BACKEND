#!/bin/bash
# Launch the FastAPI WebSocket gateway for development
# Added 2025-07-05: Updated to use uv and new gateway structure

set -e

echo "Starting FastAPI WebSocket Gateway..."
echo "Server will be available at http://127.0.0.1:8000"
echo "WebSocket endpoint at ws://127.0.0.1:8000/ws"

# Run with uv
cd "$(dirname "$0")/.."
uv run python src/main.py
