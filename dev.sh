#!/usr/bin/env bash
set -e

read -p "Porta do backend [8000]: " port
port=${port:-8000}
export JARVIS_PORT="$port"

echo "Backend na porta $port | Frontend em http://localhost:5173"

jarvis-api &
BACKEND_PID=$!
trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM

cd frontend && npm run dev
