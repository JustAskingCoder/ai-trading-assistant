#!/usr/bin/env bash
# AI Trading Assistant - Local Start Script
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "  AI Trading Assistant — Launching Services       "
echo "=================================================="

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r backend/requirements.txt
fi

# Ensure database is initialized
./venv/bin/python -m backend.database.init_db

# Start backend
echo "Starting Backend on http://127.0.0.1:8000 ..."
PYTHONPATH=. ./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting Frontend on http://127.0.0.1:5173 ..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

cd "$PROJECT_ROOT"
echo ""
echo "Both services are running:"
echo "  • Web Terminal: http://127.0.0.1:5173"
echo "  • REST API:     http://127.0.0.1:8000"
echo "  • Swagger Docs: http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to terminate both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
