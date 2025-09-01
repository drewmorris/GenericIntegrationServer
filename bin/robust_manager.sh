#!/bin/bash
# Robust Container Management System
# Single script to handle all container operations safely

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.robust_manager.pids"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/robust_manager.log"
}

cleanup_processes() {
    log "🧹 Cleaning up any leftover processes..."
    
    # Kill any web development servers
    pkill -f "vite" 2>/dev/null || true
    pkill -f "http.server" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "celery" 2>/dev/null || true
    pkill -f "act" 2>/dev/null || true
    
    # Clean up any existing PID files
    rm -f "$PID_FILE" "$PROJECT_ROOT/.simple_pids" 2>/dev/null || true
    
    # Wait a moment for processes to terminate gracefully
    sleep 2
    
    log "✅ Process cleanup completed"
}

fix_permissions() {
    log "🔧 Fixing file permissions..."
    
    # Fix ownership of key files to vscode user
    sudo chown -R vscode:vscode "$PROJECT_ROOT/.venv" 2>/dev/null || true
    sudo chown -R vscode:vscode "$PROJECT_ROOT/web/node_modules" 2>/dev/null || true
    sudo chown -R vscode:vscode "$PROJECT_ROOT/.mypy_cache" 2>/dev/null || true
    sudo chown -R vscode:vscode "$PROJECT_ROOT/.pytest_cache" 2>/dev/null || true
    sudo chown vscode:vscode "$PROJECT_ROOT/poetry.toml" 2>/dev/null || true
    
    log "✅ Permission fixes completed"
}

check_environment() {
    log "🔍 Checking environment setup..."
    
    # Check Python virtual environment
    if [[ ! -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
        log "⚠️  Python virtual environment missing, recreating..."
        cd "$PROJECT_ROOT"
        python -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip poetry
        poetry install
    fi
    
    # Check pnpm installation
    if ! command -v pnpm >/dev/null 2>&1; then
        log "⚠️  pnpm missing, installing..."
        npm install -g pnpm
    fi
    
    # Check web dependencies
    if [[ ! -d "$PROJECT_ROOT/web/node_modules" ]]; then
        log "⚠️  Web dependencies missing, installing..."
        cd "$PROJECT_ROOT/web"
        pnpm install
    fi
    
    log "✅ Environment check completed"
}

run_incremental_tests() {
    log "🧪 Running incremental tests to verify fixes..."
    
    cd "$PROJECT_ROOT"
    
    # Test 1: Python linting
    log "📝 Testing Python linting..."
    if poetry run ruff check tests/integration/test_auth_routes_integration.py; then
        log "✅ Python linting: PASSED"
    else
        log "❌ Python linting: FAILED"
        return 1
    fi
    
    # Test 2: MyPy type checking (sample file)
    log "🔍 Testing MyPy type checking..."
    if poetry run mypy backend/api/routes.py; then
        log "✅ MyPy type checking: PASSED"
    else
        log "❌ MyPy type checking: FAILED"
        return 1
    fi
    
    # Test 3: Web formatting check
    log "💄 Testing web formatting..."
    cd web
    if pnpm run format:check >/dev/null 2>&1; then
        log "✅ Web formatting: PASSED"
    else
        log "❌ Web formatting: FAILED"
        return 1
    fi
    
    # Test 4: TypeScript compilation
    log "📜 Testing TypeScript compilation..."
    if pnpm run tsc:check; then
        log "✅ TypeScript compilation: PASSED"
    else
        log "❌ TypeScript compilation: FAILED"
        return 1
    fi
    
    log "🎉 All incremental tests passed!"
    return 0
}

start_development_servers() {
    log "🚀 Starting development servers..."
    
    cd "$PROJECT_ROOT"
    
    # Start backend
    log "Starting backend server..."
    poetry run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "BACKEND_PID=$BACKEND_PID" >> "$PID_FILE"
    
    # Start frontend
    log "Starting frontend server..."
    cd web
    pnpm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "FRONTEND_PID=$FRONTEND_PID" >> "$PID_FILE"
    
    cd "$PROJECT_ROOT"
    log "✅ Development servers started"
    log "   Backend: http://localhost:8000"
    log "   Frontend: http://localhost:5173"
    log "   PIDs saved to: $PID_FILE"
}

stop_development_servers() {
    log "🛑 Stopping development servers..."
    
    if [[ -f "$PID_FILE" ]]; then
        while IFS= read -r line; do
            if [[ "$line" =~ ^([A-Z_]+)_PID=([0-9]+)$ ]]; then
                NAME="${BASH_REMATCH[1]}"
                PID="${BASH_REMATCH[2]}"
                log "Stopping $NAME (PID: $PID)..."
                kill "$PID" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    cleanup_processes
    log "✅ Development servers stopped"
}

show_help() {
    cat << EOF
🛠️  Robust Container Manager

Usage: $0 <command>

Commands:
    init        - Initialize fresh container (cleanup + setup)
    test        - Run incremental tests to verify fixes
    start       - Start development servers
    stop        - Stop all development servers
    restart     - Stop and start servers
    status      - Show system status
    cleanup     - Clean up processes and files
    help        - Show this help message

Examples:
    $0 init     # Fresh start after container rebuild
    $0 test     # Quick verification our fixes work
    $0 start    # Start both backend and frontend
    $0 stop     # Clean shutdown of all servers
EOF
}

show_status() {
    log "📊 System Status Report"
    log "======================"
    
    # Check processes
    if pgrep -f uvicorn >/dev/null 2>&1; then
        log "🟢 Backend server: RUNNING"
    else
        log "🔴 Backend server: STOPPED"
    fi
    
    if pgrep -f vite >/dev/null 2>&1; then
        log "🟢 Frontend server: RUNNING"
    else
        log "🔴 Frontend server: STOPPED"
    fi
    
    # Check environment
    if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
        log "🟢 Python virtual env: AVAILABLE"
    else
        log "🔴 Python virtual env: MISSING"
    fi
    
    if command -v pnpm >/dev/null 2>&1; then
        log "🟢 pnpm: AVAILABLE"
    else
        log "🔴 pnpm: MISSING"
    fi
    
    # Check key directories
    if [[ -d "$PROJECT_ROOT/web/node_modules" ]]; then
        log "🟢 Web dependencies: INSTALLED"
    else
        log "🔴 Web dependencies: MISSING"
    fi
}

main() {
    case "${1:-help}" in
        init)
            log "🚀 Initializing fresh container..."
            cleanup_processes
            fix_permissions
            check_environment
            log "🎉 Container initialization completed!"
            ;;
        test)
            log "🧪 Running incremental tests..."
            run_incremental_tests
            ;;
        start)
            start_development_servers
            ;;
        stop)
            stop_development_servers
            ;;
        restart)
            stop_development_servers
            sleep 2
            start_development_servers
            ;;
        status)
            show_status
            ;;
        cleanup)
            cleanup_processes
            fix_permissions
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log "❌ Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"





