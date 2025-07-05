#!/bin/bash
# Lint script updated for uv - 2025-07-05
set -e

echo "Running Ruff..."
uv run ruff check src/ tests/

echo "Running Black..."
uv run black --check src/ tests/
