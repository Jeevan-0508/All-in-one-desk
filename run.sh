#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python 3 was not found. Install it from https://www.python.org/downloads/"
    exit 1
fi

setup=""
if [ ! -x ".venv/bin/python" ]; then
    setup=1
    echo "First run - setting up. This takes a minute, only happens once."
    "$PY" -m venv .venv
elif ! cmp -s requirements.txt .venv/requirements.stamp; then
    setup=1
    echo "Dependencies changed - updating."
fi

if [ -n "$setup" ]; then
    .venv/bin/python -m pip install --upgrade pip --quiet
    .venv/bin/python -m pip install -r requirements.txt --quiet
    cp requirements.txt .venv/requirements.stamp
    echo "Setup complete."
fi

echo "Starting All-in-One Desk - press Ctrl+C to stop it."
exec .venv/bin/python app.py
