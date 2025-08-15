#!/usr/bin/env bash
# Helper script to manage persistent test containers
# Usage:
#   bin/manage_test_containers.sh start    # Start containers
#   bin/manage_test_containers.sh stop     # Stop containers
#   bin/manage_test_containers.sh restart  # Restart containers
#   bin/manage_test_containers.sh status   # Show container status
#   bin/manage_test_containers.sh reset    # Reset database schema only
#   bin/manage_test_containers.sh clean    # Stop and remove containers

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

PG_CONT_NAME="gis_ci_pg_persistent"
REDIS_CONT_NAME="gis_ci_redis_persistent"

log() { echo -e "\033[1;36m$*\033[0m"; }

case "${1:-status}" in
  start)
    log "🚀 Starting persistent test containers"
    
    # Start Postgres
    if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      if docker ps -a --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
        log "▶️  Restarting existing Postgres container"
        docker start "$PG_CONT_NAME"
      else
        log "▶️  Creating new Postgres container"
        docker run -d --name "$PG_CONT_NAME" \
          -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
          -e POSTGRES_DB=integration_server -p 5432:5432 postgres:15-alpine
      fi
    else
      log "✅ Postgres already running"
    fi
    
    # Start Redis
    if ! docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
      if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
        log "▶️  Restarting existing Redis container"
        docker start "$REDIS_CONT_NAME"
      else
        log "▶️  Creating new Redis container"
        docker run -d --name "$REDIS_CONT_NAME" -p 6379:6379 redis:7-alpine
      fi
    else
      log "✅ Redis already running"
    fi
    
    # Wait for Postgres to be ready
    log "⏳ Waiting for Postgres to be ready"
    for i in {1..30}; do
      if docker exec "$PG_CONT_NAME" pg_isready -U postgres >/dev/null 2>&1; then 
        log "✅ All containers ready"
        break
      fi
      sleep 1
    done
    ;;
    
  stop)
    log "🛑 Stopping persistent test containers"
    docker stop "$PG_CONT_NAME" "$REDIS_CONT_NAME" 2>/dev/null || true
    log "✅ Containers stopped"
    ;;
    
  restart)
    log "🔄 Restarting persistent test containers"
    docker restart "$PG_CONT_NAME" "$REDIS_CONT_NAME" 2>/dev/null || true
    log "✅ Containers restarted"
    ;;
    
  status)
    log "📊 Container Status"
    echo "Postgres ($PG_CONT_NAME):"
    if docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      echo "  ✅ Running on port 5432"
    elif docker ps -a --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      echo "  ⏸️  Stopped (exists)"
    else
      echo "  ❌ Not created"
    fi
    
    echo "Redis ($REDIS_CONT_NAME):"
    if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
      echo "  ✅ Running on port 6379"
    elif docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
      echo "  ⏸️  Stopped (exists)"
    else
      echo "  ❌ Not created"
    fi
    ;;
    
  reset)
    log "🔄 Resetting database schema only"
    if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      log "❌ Postgres container not running. Start it first with: $0 start"
      exit 1
    fi
    
    python - <<PY
from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from sqlalchemy import text

url = "postgresql://postgres:postgres@localhost:5432/integration_server"
cfg = Config("backend/alembic.ini")
cfg.set_main_option("sqlalchemy.url", url)

try:
    print("🔄 Resetting database schema...")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    print("✅ Database schema reset complete")
except Exception as e:
    print(f"⚠️  Schema reset failed: {e}")
    # Fallback: drop tables manually
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename != 'alembic_version'
        """))
        tables = [row[0] for row in result]
        
        if tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {', '.join(tables)} CASCADE"))
            conn.commit()
            print(f"🗑️  Dropped {len(tables)} tables manually")
        
        command.upgrade(cfg, "head")
        print("✅ Database schema recreated")
PY
    ;;
    
  clean)
    log "🧹 Cleaning up persistent test containers"
    docker stop "$PG_CONT_NAME" "$REDIS_CONT_NAME" 2>/dev/null || true
    docker rm "$PG_CONT_NAME" "$REDIS_CONT_NAME" 2>/dev/null || true
    log "✅ Containers stopped and removed"
    ;;
    
  *)
    echo "Usage: $0 {start|stop|restart|status|reset|clean}"
    echo ""
    echo "Commands:"
    echo "  start    - Start persistent test containers"
    echo "  stop     - Stop containers (keep them for restart)"
    echo "  restart  - Restart existing containers"
    echo "  status   - Show current container status"
    echo "  reset    - Reset database schema only (fast)"
    echo "  clean    - Stop and remove containers completely"
    exit 1
    ;;
esac
