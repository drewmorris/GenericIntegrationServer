#!/usr/bin/env bash
# Virtual Environment-based startup script
# Uses proper virtual environment instead of broken Poetry configuration

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m[$(date '+%H:%M:%S')] ✅ $*\033[0m"; }
error() { echo -e "\033[1;31m[$(date '+%H:%M:%S')] ❌ $*\033[0m"; }

# Load system configuration
if [[ ! -f .system_config ]]; then
    error "System not initialized. Run: ./init_system.sh"
    exit 1
fi

source .system_config

log "🚀 Starting Integration Server with Virtual Environment..."

# Step 1: Verify virtual environment exists
if [[ ! -d "$VENV_PATH" ]]; then
    error "Virtual environment not found at: $VENV_PATH"
    error "Run: ./init_system.sh to initialize the system"
    exit 1
fi

# Step 2: Kill any existing processes
log "1️⃣ Stopping existing processes..."
pkill -f "uvicorn.*backend.main" 2>/dev/null || true
pkill -f "vite.*--port.*5173" 2>/dev/null || true
pkill -f "node.*dev" 2>/dev/null || true
sleep 2

# Step 3: Verify core services are running
log "2️⃣ Verifying core services..."
if ! docker ps --format '{{.Names}}' | grep -q "gis_pg"; then
    error "PostgreSQL container not running. Run: ./init_system.sh"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "gis_redis"; then
    error "Redis container not running. Run: ./init_system.sh"  
    exit 1
fi

# Step 4: Source environment variables
log "3️⃣ Loading environment variables..."
source .core_env

# Step 5: Start backend with virtual environment
log "4️⃣ Starting backend server with virtual environment..."

# Activate virtual environment from root directory
source "$VENV_PATH/bin/activate"
cd "$BACKEND_PATH"

# Verify boto3 is available
python -c "import boto3; print('✅ boto3 available:', boto3.__version__)" || {
    error "boto3 not available in virtual environment"
    exit 1
}

# Start backend in background
log "Starting backend: PYTHONPATH=$PYTHONPATH python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
PYTHONPATH="$PYTHONPATH" python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Step 6: Wait for backend to be ready
log "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        success "Backend is ready!"
        break
    fi
    
    if [[ $i -eq 30 ]]; then
        error "Backend failed to start within 30 seconds"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    if [[ $((i % 5)) -eq 0 ]]; then
        log "Still waiting for backend... ($i/30)"
    fi
    
    sleep 1
done

# Step 7: Start frontend
log "5️⃣ Starting frontend server..."
cd "$FRONTEND_PATH"

npm run dev -- --port 5173 --host 0.0.0.0 &
FRONTEND_PID=$!

# Step 8: Wait for frontend to be ready  
log "⏳ Waiting for frontend to be ready..."
for i in {1..20}; do
    if curl -s http://localhost:5173 >/dev/null 2>&1; then
        success "Frontend is ready!"
        break
    fi
    
    if [[ $i -eq 20 ]]; then
        error "Frontend failed to start within 20 seconds"
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    
    if [[ $((i % 5)) -eq 0 ]]; then
        log "Still waiting for frontend... ($i/20)"
    fi
    
    sleep 1
done

# Step 9: Success!
success "🌟 Integration Server Started Successfully!"
log ""
log "✅ 📍 Services:"
log "✅    Backend API: http://localhost:8000"
log "✅    API Docs: http://localhost:8000/docs" 
log "✅    Web Interface: http://localhost:5173"
log ""
log "✅ 📋 Ready for testing:"
log "✅    1. Open http://localhost:5173 in your browser"
log "✅    2. Login with your account"
log "✅    3. Test Gmail connector (boto3 is now available!)"
log ""
log "💡 Management Commands:"
log "   ./stop_venv_system.sh  - Stop all services"
log "   ./status_system.sh     - Check service status"

# Save PIDs for cleanup script
cat > .system_pids <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF

log "✅ System is running (PIDs saved for cleanup)"


