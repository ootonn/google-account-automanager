#!/bin/bash

cd "$(dirname "$0")/.."

BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "Starting Auto BitBrowser Web API..."
echo "API URL: http://127.0.0.1:${BACKEND_PORT}"
echo "Docs   : http://127.0.0.1:${BACKEND_PORT}/docs"
echo ""

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python -m uvicorn web.backend.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
