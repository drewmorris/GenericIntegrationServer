#!/usr/bin/env bash
# Start/verify Postgres and Redis via Docker and run Alembic migrations.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

log() { echo -e "\033[1;36m$*\033[0m"; }

POSTGRES_IMAGE="postgres:15-alpine"
REDIS_IMAGE="redis:7-alpine"
PG_CONT_NAME="gis_pg"
REDIS_CONT_NAME="gis_redis"

# Ensure docker availability or try DOCKER_HOST fallback already handled by setup_docker_access
if ! command -v docker >/dev/null 2>&1; then
  log "⚠️  Docker CLI not found; trying to set up access"
  if [[ -x "$ROOT_DIR/bin/setup_docker_access.sh" ]]; then
    bash "$ROOT_DIR/bin/setup_docker_access.sh" || true
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  log "⚠️  Docker not available; skipping containerized services"
  exit 0
fi

docker pull "$POSTGRES_IMAGE" >/dev/null 2>&1 || true
docker pull "$REDIS_IMAGE" >/dev/null 2>&1 || true

# Start Postgres if not running; do not bind host port to avoid conflicts
if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
  log "▶️  Starting Postgres container $PG_CONT_NAME"
  docker run -d --restart unless-stopped --name "$PG_CONT_NAME" \
    -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=integration_server "$POSTGRES_IMAGE" >/dev/null
fi

# Wait for Postgres readiness
log "⏳ Waiting for Postgres to be ready"
for i in {1..60}; do
  if docker exec "$PG_CONT_NAME" pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Resolve Postgres container IP
PG_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PG_CONT_NAME" 2>/dev/null || echo "")
if [[ -z "$PG_IP" ]]; then
  PG_IP="host.docker.internal"
fi

# Start Redis if not running
if ! docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
  log "▶️  Starting Redis container $REDIS_CONT_NAME"
  docker run -d --restart unless-stopped --name "$REDIS_CONT_NAME" "$REDIS_IMAGE" >/dev/null
fi

# Resolve Redis IP
REDIS_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$REDIS_CONT_NAME" 2>/dev/null || echo "")
if [[ -z "$REDIS_IP" ]]; then
  REDIS_IP="host.docker.internal"
fi

# Export connection info and write .core_env
POSTGRES_HOST="$PG_IP"
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=integration_server
REDIS_URL="redis://$REDIS_IP:6379/0"

cat > "$ROOT_DIR/.core_env" <<ENV
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
REDIS_URL=$REDIS_URL
CELERY_BROKER_URL=$REDIS_URL
CELERY_RESULT_BACKEND=$REDIS_URL
ENV

log "✅ Core service endpoints written to .core_env"

# Run Alembic migrations against container IP
export DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
python - <<PY || true
from alembic.config import Config
from alembic import command
cfg = Config("backend/alembic.ini")
cfg.set_main_option("sqlalchemy.url", "$DATABASE_URL")
try:
    command.upgrade(cfg, "head")
    print("Alembic upgrade head OK →", "$DATABASE_URL")
except Exception as e:
    print("Alembic migration failed:", e)
PY

log "✅ Core services ready"


