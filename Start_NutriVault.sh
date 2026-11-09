#!/bin/bash
# NutriVault One-Stop Desktop Launcher for Linux
set -e

cd "$(dirname "$0")"

echo "==========================================================="
echo "  🥗 Starting NutriVault (Local-First Nutrition Tracker)   "
echo "==========================================================="
echo "  Your web browser will open automatically in a moment..."
echo "  (Keep this window open while using NutriVault; close it  "
echo "   or press Ctrl+C when you are done.)                     "
echo "==========================================================="

# 1. If Docker is running, start turnkey Docker stack
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "-> Docker detected. Starting NutriVault + Camera AI sidecar..."
    if command -v xdg-open >/dev/null 2>&1; then
        (sleep 2 && xdg-open "http://localhost:8080") &
    fi
    docker compose up
    exit 0
fi

# 2. Otherwise use portable uv (installing to ~/.local/bin if not yet present)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    echo "-> Installing lightweight Python environment manager (one-time setup)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo "-> Starting NutriVault on http://localhost:8080 ..."
uv run python -m src.api --open-browser
