#!/usr/bin/env bash
# Simplified startup script that works around Docker/WSL2 EIO issues

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m[$(date '+%H:%M:%S')] ✅ $*\033[0m"; }
error() { echo -e "\033[1;31m[$(date '+%H:%M:%S')] ❌ $*\033[0m"; }
warn() { echo -e "\033[1;33m[$(date '+%H:%M:%S')] ⚠️  $*\033[0m"; }

log "🚀 Simple Integration Server Startup (EIO-resistant)..."

# Step 1: Start core services
log "1️⃣ Starting core services..."
bash bin/start_core_services.sh || {
    error "Failed to start core services"
    exit 1
}

# Step 2: Use existing venv if available, otherwise minimal setup
log "2️⃣ Setting up Python environment..."
if [[ ! -d .venv ]]; then
    log "Creating minimal virtual environment..."
    python3 -m venv .venv --clear
    source .venv/bin/activate
    log "Installing minimal dependencies..."
    pip install --no-cache-dir fastapi uvicorn boto3 psycopg2-binary alembic sqlalchemy
else
    source .venv/bin/activate
fi

# Step 3: Run migrations
log "3️⃣ Running database migrations..."
set -a
source .core_env 2>/dev/null || true
set +a
export DATABASE_URL="postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-integration_server}"
cd backend
PYTHONPATH="$ROOT_DIR" python -m alembic upgrade head || warn "Migration failed - continuing anyway"
cd "$ROOT_DIR"

# Step 4: Skip frontend for now (due to npm EIO issues)
warn "4️⃣ Skipping frontend setup due to EIO errors - starting backend only"

# Step 5: Start backend  
log "5️⃣ Starting backend server..."

# Kill any existing processes
pkill -f "uvicorn.*backend.main" 2>/dev/null || true
sleep 2

cd backend
PYTHONPATH="$ROOT_DIR" python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd "$ROOT_DIR"

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
        exit 1
    fi
    sleep 1
done

# Save PID for cleanup
echo "BACKEND_PID=$BACKEND_PID" > .simple_pids

success "🌟 Backend Started Successfully!"
log ""
log "✅ 📍 Services:"
log "✅    Backend API: http://localhost:8000"
log "✅    API Docs: http://localhost:8000/docs"
log ""
log "💡 Management:"
log "   kill \$(cat .simple_pids | cut -d= -f2)  - Stop backend"
log "   tail -f logs/backend.log                - View backend logs"
