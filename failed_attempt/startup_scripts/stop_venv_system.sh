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
pkill -9 -f "python.*backend\.main" 2>/dev/null || true
pkill -9 -f "python.*uvicorn.*backend" 2>/dev/null || true
pkill -9 -f ".venv.*python.*main:app" 2>/dev/null || true
pkill -9 -f "multiprocessing.*spawn.*" 2>/dev/null || true
pkill -9 -f "vite.*--port.*5173" 2>/dev/null || true
pkill -9 -f "node.*dev" 2>/dev/null || true
pkill -9 -f "node.*vite" 2>/dev/null || true
pkill -9 -f "esbuild.*--service" 2>/dev/null || true
pkill -9 -f "pnpm.*dev" 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Verify ports are free using alternative methods (lsof/fuser may not be available)
check_port_free() {
    local port=$1
    local name=$2
    
    # Try multiple methods to check port
    if command -v lsof >/dev/null 2>&1; then
        if ! lsof -i :$port >/dev/null 2>&1; then
            success "Port $port is free"
            return 0
        fi
    elif command -v ss >/dev/null 2>&1; then
        if ! ss -tln | grep -q ":$port "; then
            success "Port $port is free"
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if ! netstat -tln | grep -q ":$port "; then
            success "Port $port is free" 
            return 0
        fi
    else
        # Fallback: try to connect to see if port responds
        if ! timeout 3 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null; then
            success "Port $port is free (connection test)"
            return 0
        fi
    fi
    
    # Port appears to be in use
    log "Port $port still in use, trying to free it..."
    if command -v fuser >/dev/null 2>&1; then
        fuser -k $port/tcp 2>/dev/null || true
    else
        log "fuser not available, using pkill for $name"
        case $port in
            8000) pkill -9 -f "python.*uvicorn\|uvicorn.*python\|backend\.main\|:8000" 2>/dev/null || true ;;
            5173) pkill -9 -f "vite.*5173\|node.*5173\|:5173" 2>/dev/null || true ;;
        esac
    fi
    sleep 1
    success "Attempted to free port $port"
}

check_port_free 8000 "backend"
check_port_free 5173 "frontend"

success "🛑 All Integration Server services stopped"














