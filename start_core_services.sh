#!/usr/bin/env bash
# Start (or verify) core infra services needed by the backend:
#   * Postgres 15 running on 5432, DB="integration_server"
#   * Redis 7 running on 6379
#
# The script is idempotent:
#   • If the containers already run it leaves them untouched.
#   • If they are missing it starts them with sensible defaults.
#   • After Postgres is ready it applies Alembic migrations so the schema exists.
#
# Usage: ./start_core_services.sh
set -euo pipefail

PG_CONT_NAME="gis-pg"
REDIS_CONT_NAME="gis-redis"

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DB=${POSTGRES_DB:-integration_server}
DEFAULT_PG_PORT=${POSTGRES_PORT:-5432}
POSTGRES_PORT=$DEFAULT_PG_PORT
POSTGRES_HOST=${POSTGRES_HOST:-localhost}

# Helper
log(){ echo -e "\033[1;36m$*\033[0m"; }

require_docker(){
  if ! command -v docker >/dev/null; then
    echo "Docker not found on PATH – cannot manage services" >&2; exit 1; fi
  if ! docker info >/dev/null 2>&1; then
    log "ℹ️  Local docker socket not reachable; trying common TCP endpoints"
    # If DOCKER_HOST already set we tried it; unset before probing
    unset DOCKER_HOST || true

    # 1. Docker Desktop default
    DOCKER_HOST=tcp://host.docker.internal:2375
    if docker info >/dev/null 2>&1; then
      export DOCKER_HOST; log "✅ Connected to Docker at $DOCKER_HOST"; return
    fi

    # 2. Default gateway (Linux containers)
    gw=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
    if [[ -n "$gw" ]]; then
      DOCKER_HOST=tcp://$gw:2375
      if docker info >/dev/null 2>&1; then
        export DOCKER_HOST; log "✅ Connected to Docker at $DOCKER_HOST"; return
      fi
    fi

    echo "Docker daemon not reachable – ensure it is running or expose the socket" >&2; exit 1
  fi
}

port_free(){ lsof -iTCP:$1 -sTCP:LISTEN -P >/dev/null 2>&1 || return 0; return 1; }

choose_free_port(){
  p=$DEFAULT_PG_PORT
  while ! port_free $p; do p=$((p+1)); done
  echo $p
}

start_postgres(){
  if docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
    log "🐳 Postgres container ${PG_CONT_NAME} already running"
  else
    if docker ps -a --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      log "▶️  Removing stopped Postgres container"; docker rm -f "$PG_CONT_NAME" >/dev/null
    fi
    # Run without host port mapping; we'll connect via container IP
    POSTGRES_PORT=5432
    log "🐳 Starting Postgres ${PG_CONT_NAME} (no host port mapping)"
    docker run -d --name "$PG_CONT_NAME" \
      -e POSTGRES_USER=$POSTGRES_USER -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
      -e POSTGRES_DB=$POSTGRES_DB postgres:15-alpine >/dev/null
  fi
  # Wait ready
  log "⏳ Waiting for Postgres to be ready"
  for i in {1..60}; do
    if docker exec "$PG_CONT_NAME" pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; then break; fi
    sleep 1
  done
}

start_redis(){
  if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
    log "🐳 Redis container ${REDIS_CONT_NAME} already running"
  else
    if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
      log "▶️  Removing stopped Redis container"; docker rm -f "$REDIS_CONT_NAME" >/dev/null
    fi
    log "🐳 Starting Redis ${REDIS_CONT_NAME} on 6379"
    docker run -d --name "$REDIS_CONT_NAME" -p 6379:6379 redis:7-alpine >/dev/null
  fi
}

run_migrations(){
  # Apply Alembic migrations using the host's python environment
  log "📜 Running Alembic migrations"
  # Wait until host-port connection works (may lag pg_isready inside container)
  for i in {1..30}; do
    python - <<PY 2>/dev/null && break || true
import psycopg2, os, sys
try:
    psycopg2.connect(host=os.getenv('POSTGRES_HOST','localhost'),
                     port=os.getenv('POSTGRES_PORT','5432'),
                     user=os.getenv('POSTGRES_USER','postgres'),
                     password=os.getenv('POSTGRES_PASSWORD','postgres'),
                     dbname=os.getenv('POSTGRES_DB','integration_server'))
except Exception as e:
    sys.exit(1)
PY
    sleep 1
  done

  python - <<PY
from alembic.config import Config
from alembic import command
import os, re
url=f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ.get('POSTGRES_HOST','localhost')}:{os.environ.get('POSTGRES_PORT','5432')}/{os.environ['POSTGRES_DB']}"
# strip +asyncpg if present
url = re.sub(r"\+.*$", "", url)
cfg=Config("backend/alembic.ini"); cfg.set_main_option("sqlalchemy.url", url)
command.upgrade(cfg, "head")
print("Alembic head applied to", url)
PY
}

main(){
  resolve_docker_host(){
    # Already set? then trust user.
    if [[ -n "${DOCKER_HOST:-}" ]]; then return; fi
    # If socket exists assume usable.
    if [[ -S /var/run/docker.sock ]]; then return; fi
    # Otherwise let require_docker attempt TCP endpoints
    DOCKER_HOST=tcp://host.docker.internal:2375; export DOCKER_HOST
  }

  resolve_docker_host
  require_docker
  start_postgres
  start_redis
  # Determine container IPs and export; persist to .core_env for caller shells
  POSTGRES_HOST=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PG_CONT_NAME")
  REDIS_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$REDIS_CONT_NAME")
  export POSTGRES_HOST POSTGRES_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB
  export REDIS_URL="redis://${REDIS_IP}:6379/0"
  {
    echo "POSTGRES_HOST=$POSTGRES_HOST"
    echo "POSTGRES_PORT=$POSTGRES_PORT"
    echo "POSTGRES_USER=$POSTGRES_USER"
    echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
    echo "POSTGRES_DB=$POSTGRES_DB"
    echo "REDIS_URL=$REDIS_URL"
  } > .core_env
  run_migrations
  log "✅ Core services are up and ready"
}

main "$@" 