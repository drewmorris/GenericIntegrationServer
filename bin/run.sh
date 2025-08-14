#!/usr/bin/env bash
# Project launcher to start/stop services from anywhere.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

usage() {
  echo "Usage: bin/run.sh [start|dev|prod|stop]"
  exit 1
}

cmd="${1:-start}"

case "$cmd" in
  start|dev)
    # Ensure core services are up
    bash "$ROOT_DIR/bin/start_core_services.sh"
    # Source connection env if present
    if [[ -f "$ROOT_DIR/.core_env" ]]; then
      # shellcheck disable=SC1091
      source "$ROOT_DIR/.core_env"
    fi
    # Start backend API
    echo "▶️  Starting backend (uvicorn)"
    if command -v poetry >/dev/null 2>&1; then
      (poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &) 
    else
      (uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &)
    fi
    # Start Celery worker + beat
    export CELERY_BROKER_URL="${CELERY_BROKER_URL:-${REDIS_URL:-redis://localhost:6379/0}}"
    export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-$CELERY_BROKER_URL}"
    echo "▶️  Starting Celery worker and beat"
    if command -v poetry >/dev/null 2>&1; then
      (poetry run celery -A backend.orchestrator worker -l info &)
      (poetry run celery -A backend.orchestrator beat -l info &)
    else
      (celery -A backend.orchestrator worker -l info &)
      (celery -A backend.orchestrator beat -l info &)
    fi
    # Start web dev server if present
    if [[ -f "$ROOT_DIR/web/package.json" ]]; then
      echo "▶️  Starting web dev server"
      (npm --prefix web run dev -- --host 0.0.0.0 &)
    fi
    echo "✅ Services started. Backend: http://localhost:8000"
    ;;
  prod)
    bash "$ROOT_DIR/bin/start_core_services.sh"
    if [[ -f "$ROOT_DIR/.core_env" ]]; then
      # shellcheck disable=SC1091
      source "$ROOT_DIR/.core_env"
    fi
    echo "▶️  Starting backend (gunicorn/uvicorn workers)"
    if command -v poetry >/dev/null 2>&1; then
      (poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &)
    else
      (uvicorn backend.main:app --host 0.0.0.0 --port 8000 &)
    fi
    export CELERY_BROKER_URL="${CELERY_BROKER_URL:-${REDIS_URL:-redis://localhost:6379/0}}"
    export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-$CELERY_BROKER_URL}"
    echo "▶️  Starting Celery worker and beat"
    if command -v poetry >/dev/null 2>&1; then
      (poetry run celery -A backend.orchestrator worker -l info &)
      (poetry run celery -A backend.orchestrator beat -l info &)
    else
      (celery -A backend.orchestrator worker -l info &)
      (celery -A backend.orchestrator beat -l info &)
    fi
    if [[ -f "$ROOT_DIR/web/package.json" ]]; then
      echo "▶️  Building and serving web app"
      npm --prefix web run build
      (npx --yes serve -s web/dist -l 5173 &)
    fi
    echo "✅ Production services started"
    ;;
  stop)
    echo "🛑 Stopping services"
    pkill -f "uvicorn backend.main:app" || true
    pkill -f "celery -A backend.orchestrator worker" || true
    pkill -f "celery -A backend.orchestrator beat" || true
    pkill -f "vite" || true
    pkill -f "serve -s web/dist" || true
    sleep 1
    echo "✅ Stopped"
    ;;
  *)
    usage
    ;;
esac


