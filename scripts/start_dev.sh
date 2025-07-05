#!/bin/bash
# Launch MCP, Router, and Gateway (SQLite-backed) in one terminal
# Assumes all services are started via Python scripts in src/

set -e

python3 src/mcp/main.py &
python3 src/router/main.py &
python3 src/gateway/main.py &
wait
