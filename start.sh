#!/usr/bin/env bash
echo "========================================================"
echo " EdgeMind AI Studio — Self-Optimizing Image Generator"
echo "========================================================"
echo ""

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[!] Warning: Dependencies check encountered warnings."
fi

echo "Starting EdgeMind server..."
python3 app.py
