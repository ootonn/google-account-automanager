#!/bin/bash

cd "$(dirname "$0")/frontend"

FRONTEND_PORT="${FRONTEND_PORT:-5173}"
VITE_BACKEND_TARGET="${VITE_BACKEND_TARGET:-http://127.0.0.1:8000}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api}"

export VITE_BACKEND_TARGET
export VITE_API_BASE_URL

echo "Starting Auto BitBrowser Web frontend..."
echo "Frontend URL : http://127.0.0.1:${FRONTEND_PORT}"
echo "Backend proxy: ${VITE_BACKEND_TARGET}"
echo ""

npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort
