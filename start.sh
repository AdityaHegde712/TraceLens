#!/usr/bin/env bash
# TraceLens: Interactive Web Dashboard Launcher

set -euo pipefail

# Ensure UTF-8 encoding
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Virtual environment detection and setup
if [ ! -d ".venv" ]; then
    echo "======================================================================"
    echo "Creating virtual environment .venv using uv..."
    echo "======================================================================"
    if command -v uv >/dev/null 2>&1; then
        uv venv --python 3.13 .venv || uv venv .venv
        uv pip install -e ".[dev]"
    else
        python3 -m venv .venv || python -m venv .venv
        if [ -f ".venv/bin/pip" ]; then
            .venv/bin/pip install -e ".[dev]"
        elif [ -f ".venv/Scripts/pip" ]; then
            .venv/Scripts/pip install -e ".[dev]"
        fi
    fi
fi

# Activate environment across platforms
if [ -f ".venv/Scripts/activate" ]; then
    # Windows Git-Bash / MSYS2
    # shellcheck source=/dev/null
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    # Linux / macOS
    # shellcheck source=/dev/null
    source .venv/bin/activate
else
    echo "Error: Virtual environment activation script not found in .venv"
    exit 1
fi

PORT="${TRACELENS_PORT:-8000}"
HOST="${TRACELENS_HOST:-127.0.0.1}"
URL="http://${HOST}:${PORT}"

echo "======================================================================"
echo " TraceLens: Evidence-Grounded Incident Triage Assistant for RAG APIs"
echo " Web UI Dashboard: ${URL}"
echo "======================================================================"

# Automatically open default browser after a brief delay
open_browser() {
    sleep 1
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then
        open "$URL" >/dev/null 2>&1 || true
    elif command -v cmd.exe >/dev/null 2>&1; then
        cmd.exe /c start "" "$URL" >/dev/null 2>&1 || true
    fi
}

open_browser &

# Launch TraceLens UI
exec tracelens ui --host "$HOST" --port "$PORT"
