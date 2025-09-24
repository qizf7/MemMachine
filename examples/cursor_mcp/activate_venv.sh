#!/bin/bash

# Activation script for Cursor MCP Server virtual environment

echo "Activating Cursor MCP Server virtual environment..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies if not already installed
echo "Installing dependencies..."
uv pip install -e .

echo "Virtual environment activated!"
echo "You can now run: python cursor_mcp_server.py"
echo "To deactivate, run: deactivate"
