#!/usr/bin/env bash
# Check Integration Server status

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m✅ $*\033[0m"; }
error() { echo -e "\033[1;31m❌ $*\033[0m"; }

log "📊 Checking Integration Server status..."

# Check virtual environment
if [[ -f .system_config ]]; then
    source .system_config
    if [[ -d "$VENV_PATH" ]]; then
        success "Virtual Environment: Ready ($VENV_PATH)"
    else
        error "Virtual Environment: Missing"
    fi
else
    error "System Configuration: Not initialized (run ./init_system.sh)"
fi

# Check core services (Docker containers)
if docker ps --format '{{.Names}}' | grep -q "gis_pg"; then
    success "PostgreSQL Container: Running"
else
    error "PostgreSQL Container: Not running"
fi

if docker ps --format '{{.Names}}' | grep -q "gis_redis"; then
    success "Redis Container: Running"  
else
    error "Redis Container: Not running"
fi

# Check backend service
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    success "Backend API: Running ($HEALTH_RESPONSE)"
    
    # Check if boto3 is available in the backend
    BOTO3_CHECK=$(curl -s http://localhost:8000/connectors/definitions 2>/dev/null | head -c 100 || echo "error")
    if [[ "$BOTO3_CHECK" != "error" ]]; then
        success "   └─ Connectors API: OK (boto3 dependencies available)"
    else
        error "   └─ Connectors API: Error"
    fi
else
    error "Backend API: Not responding (http://localhost:8000/health)"
fi

# Check frontend service
if curl -s http://localhost:5173 >/dev/null 2>&1; then
    success "Frontend Web UI: Running"
else
    error "Frontend Web UI: Not responding (http://localhost:5173)"
fi

# Show process information
if [[ -f .system_pids ]]; then
    source .system_pids
    log "📋 Process Information:"
    if ps -p ${BACKEND_PID:-0} >/dev/null 2>&1; then
        log "   Backend PID: $BACKEND_PID (running)"
    else
        log "   Backend PID: $BACKEND_PID (not found)"
    fi
    
    if ps -p ${FRONTEND_PID:-0} >/dev/null 2>&1; then
        log "   Frontend PID: $FRONTEND_PID (running)"
    else
        log "   Frontend PID: $FRONTEND_PID (not found)"
    fi
else
    log "📋 No PID file found (.system_pids)"
fi

log ""
log "💡 Available commands:"
log "   ./init_system.sh       - Initialize/reinitialize system"
log "   ./start_venv_system.sh  - Start all services"  
log "   ./stop_venv_system.sh   - Stop all services"
log "   ./status_system.sh      - Show this status"














