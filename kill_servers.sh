#!/bin/bash
# Quick server shutdown script
echo "🛑 Force stopping all Integration Server processes..."

# Kill by process pattern (most aggressive)
pkill -9 -f "uvicorn.*backend.main" 2>/dev/null || true
pkill -9 -f "vite.*--port.*5173" 2>/dev/null || true
pkill -9 -f "node.*vite" 2>/dev/null || true
pkill -9 -f "esbuild.*--service" 2>/dev/null || true

# Kill by port (backup method)
for port in 8000 5173; do
    pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill -9 $pid 2>/dev/null || true
        echo "  Killed process on port $port (PID: $pid)"
    fi
done

# Clean up PID files
rm -f .backend.pid .frontend.pid 2>/dev/null

# Verify ports are free
sleep 1
for port in 8000 5173; do
    if lsof -i :$port >/dev/null 2>&1; then
        echo "❌ Port $port is still in use"
    else
        echo "✅ Port $port is free"
    fi
done

echo "✅ All servers stopped"
