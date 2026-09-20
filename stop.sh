#!/usr/bin/env bash
# AI Trading Assistant - Local Stop Script
echo "Stopping AI Trading Assistant processes on ports 8000 and 5173..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
echo "All AI Trading Assistant services stopped."
