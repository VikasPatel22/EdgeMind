#!/usr/bin/env bash
set -e

echo "========================================================"
echo " EdgeMind AI Studio — Self-Optimizing Image Generator"
echo "========================================================"
echo ""

# Navigate to script directory
cd "$(dirname "$0")"

# Detect and activate virtual environment if present
if [ -f "venv/bin/activate" ]; then
    echo "[*] Activating virtual environment (venv)..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source .venv/bin/activate
fi

# Detect python command
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[X] Error: Python 3 was not found in PATH."
    echo "Please install Python 3.10+ before running EdgeMind."
    exit 1
fi

echo "[*] Checking dependencies..."
$PY_CMD -m pip install -r requirements.txt || {
    echo "[!] Warning: Dependencies check encountered warnings. Continuing..."
}

echo ""
echo "[*] Starting EdgeMind server on port 7265..."
$PY_CMD app.py
