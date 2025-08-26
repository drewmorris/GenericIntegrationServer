#!/usr/bin/env bash
# Stop Integration Server services

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m[$(date '+%H:%M:%S')] ✅ $*\033[0m"; }
error() { echo -e "\033[1;31m[$(date '+%H:%M:%S')] ❌ $*\033[0m"; }

log "🛑 Stopping Integration Server services..."

# Stop services using PIDs if available
if [[ -f .system_pids ]]; then
    source .system_pids
    
    if [[ -n "${BACKEND_PID:-}" ]]; then
        log "Stopping backend server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [[ -n "${FRONTEND_PID:-}" ]]; then
        log "Stopping frontend server (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Clean up PID file
    rm -f .system_pids
fi

# Aggressive cleanup using process names
log "Performing aggressive process cleanup..."
pkill -9 -f "uvicorn.*backend.main" 2>/dev/null || true
pkill -9 -f "vite.*--port.*5173" 2>/dev/null || true
pkill -9 -f "node.*dev" 2>/dev/null || true
pkill -9 -f "node.*vite" 2>/dev/null || true
pkill -9 -f "esbuild.*--service" 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Verify ports are free
if ! lsof -i :8000 >/dev/null 2>&1; then
    success "Port 8000 is free"
else
    log "Port 8000 still in use, trying to free it..."
    fuser -k 8000/tcp 2>/dev/null || true
fi

if ! lsof -i :5173 >/dev/null 2>&1; then
    success "Port 5173 is free"
else
    log "Port 5173 still in use, trying to free it..."  
    fuser -k 5173/tcp 2>/dev/null || true
fi

success "🛑 All Integration Server services stopped"

