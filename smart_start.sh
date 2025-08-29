#!/usr/bin/env bash
# Smart startup script with automatic initialization detection and idempotent setup

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m[$(date '+%H:%M:%S')] ✅ $*\033[0m"; }
error() { echo -e "\033[1;31m[$(date '+%H:%M:%S')] ❌ $*\033[0m"; }
warn() { echo -e "\033[1;33m[$(date '+%H:%M:%S')] ⚠️  $*\033[0m"; }

log "🤖 Smart Integration Server Startup..."

# Function to check if initialization is needed
needs_initialization() {
    local needs_init=false
    local reasons=()
    
    # Check for system configuration
    if [[ ! -f .system_config ]]; then
        needs_init=true
        reasons+=("Missing system configuration (.system_config)")
    fi
    
    # Check for virtual environment
    if [[ ! -d .venv ]]; then
        needs_init=true
        reasons+=("Missing virtual environment (.venv)")
    fi
    
    # Check for core dependencies in venv
    if [[ -d .venv ]]; then
        if ! .venv/bin/python -c "import boto3, fastapi, uvicorn" 2>/dev/null; then
            needs_init=true
            reasons+=("Missing dependencies in virtual environment")
        fi
    fi
    
    # Check for core services
    if ! docker ps --format '{{.Names}}' | grep -q "gis_pg"; then
        needs_init=true
        reasons+=("PostgreSQL container not running")
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "gis_redis"; then
        needs_init=true
        reasons+=("Redis container not running")
    fi
    
    if [[ "$needs_init" == "true" ]]; then
        warn "Initialization needed. Reasons:"
        for reason in "${reasons[@]}"; do
            warn "  - $reason"
        done
        return 0  # needs initialization
    else
        return 1  # no initialization needed
    fi
}

# Function to run idempotent initialization
run_initialization() {
    log "🔧 Running automatic initialization..."
    
    # Step 1: Docker access
    log "1️⃣ Setting up Docker access..."
    if [[ -e /var/run/docker.sock ]]; then
        sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
    fi
    
    # Step 2: Core services (idempotent - won't recreate existing containers)
    log "2️⃣ Ensuring core services are running..."
    bash bin/start_core_services.sh || {
        error "Failed to start core services"
        return 1
    }
    
    # Step 3: Virtual environment (idempotent)
    log "3️⃣ Setting up virtual environment..."
    
    # Set up Poetry virtual environment (like CI does)
    log "Setting up Poetry virtual environment..."
    
    # Ensure Poetry creates virtual environments (fix the root cause)
    echo '[tool.poetry.virtualenvs]' > poetry.toml
    echo 'create = true' >> poetry.toml
    echo 'in-project = true' >> poetry.toml
    
    # Create virtual environment if needed
    if [[ ! -d .venv ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    log "Installing/verifying dependencies using Poetry..."
    poetry install --with dev --no-interaction
    
    # Activate virtual environment after Poetry sets it up
    source .venv/bin/activate
    
    # Step 4: Frontend dependencies (idempotent)
    log "4️⃣ Setting up frontend dependencies..."
    cd web
    if [[ ! -d node_modules ]] || [[ package.json -nt node_modules ]]; then
        log "Installing frontend dependencies with pnpm..."
        export PATH="$HOME/.local/share/pnpm:$PATH"
        pnpm install --no-verify-store-integrity
    else
        log "Frontend dependencies up to date"
    fi
    cd ..
    
    # Step 5: Database migrations (idempotent - Alembic handles this)  
    log "5️⃣ Running database migrations..."
    cd "$ROOT_DIR"
    source .venv/bin/activate
    # Export environment variables for migrations
    set -a
    source .core_env
    set +a
    export DATABASE_URL="postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-integration_server}"
    # Run Alembic from backend directory using relative alembic.ini
    cd backend
    PYTHONPATH="$ROOT_DIR" python -m alembic upgrade head
    cd "$ROOT_DIR"
    
    # Step 6: Create/update configuration
    log "6️⃣ Creating system configuration..."
    cat > .system_config <<EOF
# Integration Server Configuration
VENV_PATH="$ROOT_DIR/.venv"
BACKEND_PATH="$ROOT_DIR/backend"
FRONTEND_PATH="$ROOT_DIR/web"
PYTHONPATH="$ROOT_DIR"
INITIALIZED_AT="$(date '+%Y-%m-%d %H:%M:%S')"
EOF
    
    success "Initialization complete!"
}

# Function to start services
start_services() {
    log "🚀 Starting services..."
    
    # Load configuration
    source .system_config
    # Export environment variables from .core_env
    set -a  # automatically export variables
    source .core_env
    set +a  # stop automatically exporting
    
    # Kill any existing processes
    pkill -f "uvicorn.*backend.main" 2>/dev/null || true
    pkill -f "vite.*--port.*5173" 2>/dev/null || true
    sleep 2
    
    # Start backend
    log "Starting backend server..."
    cd "$ROOT_DIR"
    source .venv/bin/activate
    
    # Verify dependencies
    python -c "import boto3; print('✅ boto3 available:', boto3.__version__)" || {
        error "boto3 not available - initialization may have failed"
        return 1
    }
    
    cd "$BACKEND_PATH"
    
    # Start backend in background
    PYTHONPATH="$PYTHONPATH" python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    
    # Wait for backend
    log "⏳ Waiting for backend..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            success "Backend ready!"
            break
        fi
        if [[ $i -eq 30 ]]; then
            error "Backend failed to start"
            kill $BACKEND_PID 2>/dev/null || true
            return 1
        fi
        sleep 1
    done
    
    # Start frontend
    log "Starting frontend server..."
    cd "$FRONTEND_PATH"
    export PATH="$HOME/.local/share/pnpm:$PATH"
    pnpm run dev -- --port 5173 --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Wait for frontend
    log "⏳ Waiting for frontend..."
    for i in {1..20}; do
        if curl -s http://localhost:5173 >/dev/null 2>&1; then
            success "Frontend ready!"
            break
        fi
        if [[ $i -eq 20 ]]; then
            error "Frontend failed to start"
            kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
            return 1
        fi
        sleep 1
    done
    
    # Save PIDs
    cat > .system_pids <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF
    
    cd "$ROOT_DIR"
    return 0
}

# Main execution flow
main() {
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Check if initialization is needed
    if needs_initialization; then
        log "🔍 System needs initialization - running automatic setup..."
        if ! run_initialization; then
            error "Initialization failed"
            exit 1
        fi
        log "✅ Auto-initialization complete"
    else
        success "System already initialized - starting services..."
    fi
    
    # Start services
    if start_services; then
        success "🌟 Integration Server Started Successfully!"
        log ""
        log "✅ 📍 Services:"
        log "✅    Backend API: http://localhost:8000"
        log "✅    API Docs: http://localhost:8000/docs"
        log "✅    Web Interface: http://localhost:5173"
        log ""
        log "✅ 🧪 Ready for testing:"
        log "✅    Gmail connector with boto3: AVAILABLE"
        log "✅    All dependencies: INSTALLED"
        log ""
        log "💡 Management Commands:"
        log "   ./smart_start.sh       - Smart startup (this script)"
        log "   ./stop_venv_system.sh  - Stop all services"
        log "   ./status_system.sh     - Check service status"
    else
        error "Failed to start services"
        exit 1
    fi
}

# Run main function
main "$@"

