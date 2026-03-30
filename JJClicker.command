#!/bin/bash
cd "$(dirname "$0")"
for PYTHON in /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
    if command -v "$PYTHON" &>/dev/null; then
        exec "$PYTHON" "$(dirname "$0")/JJClicker.py"
    fi
done
