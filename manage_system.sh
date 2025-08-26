#!/bin/bash
# Enhanced Integration Server Management Script
# Usage: ./manage_system.sh [start|stop|restart|status|logs]

set -e

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"
BACKEND_LOG="logs/backend.log"
FRONTEND_LOG="logs/frontend.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create logs directory
mkdir -p logs

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if a port is in use
port_in_use() {
    # Try multiple methods since lsof may not be available
    if command -v lsof >/dev/null 2>&1; then
        lsof -i :$1 >/dev/null 2>&1
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tlnp 2>/dev/null | grep ":$1 " >/dev/null
    elif command -v ss >/dev/null 2>&1; then
        ss -tlnp 2>/dev/null | grep ":$1 " >/dev/null
    else
        # Fallback: try to connect to the port
        timeout 1 bash -c "</dev/tcp/localhost/$1" >/dev/null 2>&1
    fi
}

# Function to get PID using a port
get_pid_by_port() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti :$1 2>/dev/null || echo ""
    else
        # Try to find PID via proc filesystem or ps
        ps aux | grep -E ":$1\b" | grep -v grep | awk '{print $2}' | head -1 || echo ""
    fi
}

# Function to kill processes gracefully
kill_process() {
    local pid=$1
    local name=$2
    local timeout=${3:-10}
    
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        log "Stopping $name (PID: $pid)..."
        kill -TERM "$pid" 2>/dev/null || true
        
        # Wait for graceful shutdown
        local count=0
        while [ $count -lt $timeout ] && kill -0 "$pid" 2>/dev/null; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            warning "$name didn't stop gracefully, force killing..."
            kill -KILL "$pid" 2>/dev/null || true
            sleep 1
        fi
        
        if kill -0 "$pid" 2>/dev/null; then
            error "Failed to stop $name"
            return 1
        else
            success "$name stopped"
            return 0
        fi
    fi
}

# Function to stop services
stop_services() {
    log "🛑 Stopping Integration Server services..."
    
    # Stop backend
    if [ -f "$BACKEND_PID_FILE" ]; then
        local backend_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
        kill_process "$backend_pid" "Backend Server"
        rm -f "$BACKEND_PID_FILE"
    else
        # Try to find by port
        local backend_pid=$(get_pid_by_port $BACKEND_PORT)
        if [ -n "$backend_pid" ]; then
            kill_process "$backend_pid" "Backend Server"
        fi
    fi
    
    # Stop frontend
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null)
        kill_process "$frontend_pid" "Frontend Server"
        rm -f "$FRONTEND_PID_FILE"
    else
        # Try to find by port
        local frontend_pid=$(get_pid_by_port $FRONTEND_PORT)
        if [ -n "$frontend_pid" ]; then
            kill_process "$frontend_pid" "Frontend Server"
        fi
    fi
    
    # Clean up any remaining processes
    pkill -f "uvicorn.*backend.main" 2>/dev/null || true
    pkill -f "vite.*--port.*$FRONTEND_PORT" 2>/dev/null || true
    pkill -f "node.*vite" 2>/dev/null || true
    pkill -f "esbuild.*--service" 2>/dev/null || true
    
    success "All services stopped"
}

# Function to check service status
check_status() {
    log "📊 Checking service status..."
    
    # Check backend
    if port_in_use $BACKEND_PORT; then
        local backend_pid=$(get_pid_by_port $BACKEND_PORT)
        success "Backend Server: Running (PID: $backend_pid, Port: $BACKEND_PORT)"
        
        # Test API health
        if curl -s "http://localhost:$BACKEND_PORT/docs" >/dev/null 2>&1; then
            success "  └─ API Health: OK"
        else
            warning "  └─ API Health: Not responding"
        fi
    else
        error "Backend Server: Not running"
    fi
    
    # Check frontend
    if port_in_use $FRONTEND_PORT; then
        local frontend_pid=$(get_pid_by_port $FRONTEND_PORT)
        success "Frontend Server: Running (PID: $frontend_pid, Port: $FRONTEND_PORT)"
        
        # Test frontend health
        if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
            success "  └─ Web UI: OK"
        else
            warning "  └─ Web UI: Not responding"
        fi
    else
        error "Frontend Server: Not running"
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local port=$1
    local name=$2
    local timeout=${3:-30}
    local count=0
    
    log "⏳ Waiting for $name to be ready (port $port)..."
    while [ $count -lt $timeout ]; do
        if port_in_use $port && curl -s "http://localhost:$port" >/dev/null 2>&1; then
            success "$name is ready!"
            return 0
        fi
        sleep 1
        ((count++))
        if [ $((count % 5)) -eq 0 ]; then
            log "  Still waiting for $name... ($count/$timeout)"
        fi
    done
    
    error "$name failed to start within ${timeout}s"
    return 1
}

# Function to start services
start_services() {
    log "🚀 Starting Integration Server System..."
    
    # Check if ports are already in use
    if port_in_use $BACKEND_PORT; then
        error "Port $BACKEND_PORT is already in use. Stop existing services first."
        return 1
    fi
    
    if port_in_use $FRONTEND_PORT; then
        error "Port $FRONTEND_PORT is already in use. Stop existing services first."
        return 1
    fi
    
    # Start core services (Docker containers) directly
    log "1️⃣ Setting up core services..."
    log "Setting up Docker access..."
    
    # Ensure Docker socket is accessible
    if [ -e /var/run/docker.sock ]; then
        sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
    fi
    
    log "Starting core services..."
    bash bin/start_core_services.sh || {
        error "Failed to start core services"
        return 1
    }
    
    success "Core services ready"
    
    # Start backend server
    log "2️⃣ Starting backend server..."
    (cd backend && PYTHONPATH=/workspaces/GenericIntegrationServer poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT) \
        > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    
    # Wait for backend to be ready
    if ! wait_for_service $BACKEND_PORT "Backend API" 30; then
        error "Backend failed to start. Check logs: $BACKEND_LOG"
        return 1
    fi
    
    # Start frontend server
    log "3️⃣ Starting frontend server..."
    cd web
    npm run dev -- --port $FRONTEND_PORT --host 0.0.0.0 > "../$FRONTEND_LOG" 2>&1 &
    echo $! > "../$FRONTEND_PID_FILE"
    cd ..
    
    # Wait for frontend to be ready
    if ! wait_for_service $FRONTEND_PORT "Web UI" 30; then
        error "Frontend failed to start. Check logs: $FRONTEND_LOG"
        return 1
    fi
    
    success "🌟 Integration Server Started Successfully!"
    echo ""
    success "📍 Services:"
    success "   Backend API: http://localhost:$BACKEND_PORT"
    success "   API Docs: http://localhost:$BACKEND_PORT/docs" 
    success "   Web Interface: http://localhost:$FRONTEND_PORT"
    echo ""
    success "📋 Next Steps:"
    success "   1. Open http://localhost:$FRONTEND_PORT in your browser"
    success "   2. Create an account or login"
    success "   3. Set up your connectors and destinations"
    echo ""
    log "💡 Management Commands:"
    log "   ./manage_system.sh status  - Check service status"
    log "   ./manage_system.sh logs    - View service logs"
    log "   ./manage_system.sh stop    - Stop all services"
}

# Function to show logs
show_logs() {
    local service=${1:-"all"}
    
    case $service in
        "backend"|"api")
            if [ -f "$BACKEND_LOG" ]; then
                log "📋 Backend Server Logs (last 50 lines):"
                echo "===========================================" 
                tail -50 "$BACKEND_LOG"
            else
                warning "No backend logs found"
            fi
            ;;
        "frontend"|"web")
            if [ -f "$FRONTEND_LOG" ]; then
                log "📋 Frontend Server Logs (last 50 lines):"
                echo "===========================================" 
                tail -50 "$FRONTEND_LOG"
            else
                warning "No frontend logs found"
            fi
            ;;
        "all"|*)
            show_logs "backend"
            echo ""
            show_logs "frontend"
            ;;
    esac
}

# Main script logic
case "${1:-start}" in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_services
        ;;
    "status")
        check_status
        ;;
    "logs")
        show_logs "${2:-all}"
        ;;
    *)
        echo "Usage: $0 [start|stop|restart|status|logs [backend|frontend]]"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services" 
        echo "  restart  - Restart all services"
        echo "  status   - Show service status"
        echo "  logs     - Show service logs"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs backend"
        echo "  $0 status"
        exit 1
        ;;
esac
