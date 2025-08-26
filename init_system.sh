#!/usr/bin/env bash
# Comprehensive system initialization script
# Sets up virtual environment, installs dependencies, and prepares the system

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m[$(date '+%H:%M:%S')] ✅ $*\033[0m"; }
error() { echo -e "\033[1;31m[$(date '+%H:%M:%S')] ❌ $*\033[0m"; }

log "🚀 Initializing Integration Server System..."

# Step 1: Set up Docker access
log "1️⃣ Setting up Docker access..."
if [[ -e /var/run/docker.sock ]]; then
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
fi

# Step 2: Start core services (PostgreSQL + Redis)
log "2️⃣ Starting core services..."
bash bin/start_core_services.sh || {
    error "Failed to start core services"
    exit 1
}

# Step 3: Create and set up virtual environment
log "3️⃣ Setting up Python virtual environment..."
cd backend

# Remove any existing virtual environment
if [[ -d .venv ]]; then
    log "Removing existing virtual environment..."
    rm -rf .venv
fi

# Create new virtual environment
log "Creating new virtual environment..."
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
log "Upgrading pip..."
pip install --upgrade pip

# Step 4: Install core backend dependencies
log "4️⃣ Installing backend dependencies..."
log "Installing core FastAPI dependencies..."
pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings

log "Installing authentication dependencies..."
pip install python-jose[cryptography] passlib[bcrypt] 

log "Installing Google/AWS connector dependencies..."
pip install boto3 google-api-python-client google-auth google-auth-oauthlib

log "Installing additional connector dependencies..."
pip install requests python-dateutil redis celery

log "Installing development dependencies..."
pip install pytest pytest-asyncio httpx

# Step 5: Install frontend dependencies
log "5️⃣ Setting up frontend..."
cd ../web
npm install

cd ..

# Step 6: Run database migrations
log "6️⃣ Running database migrations..."
cd backend
source .venv/bin/activate
export DATABASE_URL="$(grep DATABASE_URL ../backend/alembic.ini | cut -d'=' -f2 | xargs || echo 'postgresql://postgres:postgres@localhost:5432/integration_server')"

# Source core environment
source ../.core_env 2>/dev/null || true

# Set database URL from environment variables
export DATABASE_URL="postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-integration_server}"

# Run migrations
PYTHONPATH="$ROOT_DIR" python -m alembic upgrade head

cd ..

# Step 7: Create startup configuration
log "7️⃣ Creating system configuration..."
cat > .system_config <<EOF
# Integration Server Configuration
VENV_PATH="$ROOT_DIR/backend/.venv"
BACKEND_PATH="$ROOT_DIR/backend"
FRONTEND_PATH="$ROOT_DIR/web"
PYTHONPATH="$ROOT_DIR"
EOF

success "🎉 System initialization complete!"
log "📋 System is ready for startup with:"
log "   Virtual Environment: $ROOT_DIR/backend/.venv"
log "   Backend Path: $ROOT_DIR/backend"  
log "   Frontend Path: $ROOT_DIR/web"
log ""
log "Next steps:"
log "1. Run: ./start_venv_system.sh"
log "2. Open: http://localhost:5173"
log "3. Test Gmail connector (boto3 is now available!)"

