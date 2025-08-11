#!/usr/bin/env bash

# Simple dev convenience script to start/stop backend, worker and web dev server.
# Usage: ./run.sh start   – start all processes
#        ./run.sh stop    – stop all previously started processes

BACK_PID_FILE=.backend.pid
CELERY_PID_FILE=.celery.pid
WEB_PID_FILE=.web.pid

start_dev() {
  # Ensure Postgres & Redis are running
  ./start_core_services.sh >/dev/null
  # Load persisted core env if available
  if [[ -f ./.core_env ]]; then
    set -a; source ./.core_env; set +a
  fi
  # Determine Redis container IP and export URL for Celery/Backend
  REDIS_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' gis-redis 2>/dev/null || true)
  if [[ -z "$REDIS_IP" || "$REDIS_IP" == "null" ]]; then
     REDIS_IP="host.docker.internal"
  fi
  export REDIS_URL="redis://${REDIS_IP}:6379/0" CELERY_BROKER_URL=$REDIS_URL CELERY_RESULT_BACKEND=$REDIS_URL

  echo "🚀 Starting backend (uvicorn)..."
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
  echo $! > $BACK_PID_FILE

  echo "🧵 Starting Celery worker..."
  celery -A backend.orchestrator.celery_app worker -l info &
  echo $! > $CELERY_PID_FILE

  echo "🌐 Starting web dev server..."
  npm --prefix web run dev -- --host 0.0.0.0 --port 5173 &
  echo $! > $WEB_PID_FILE

  echo "✅ All services started (backend:8000, web:5173)"
}

start_prod() {
  # Ensure Postgres & Redis are running
  ./start_core_services.sh >/dev/null
  if [[ -f ./.core_env ]]; then
    set -a; source ./.core_env; set +a
  fi
  REDIS_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' gis-redis 2>/dev/null || true)
  if [[ -z "$REDIS_IP" || "$REDIS_IP" == "null" ]]; then
      REDIS_IP="host.docker.internal"
  fi
  export REDIS_URL="redis://${REDIS_IP}:6379/0" CELERY_BROKER_URL=$REDIS_URL CELERY_RESULT_BACKEND=$REDIS_URL
  echo "🚀 Starting backend (gunicorn)..."
  gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 &
  echo $! > $BACK_PID_FILE

  echo "🧵 Starting Celery worker (prod)..."
  celery -A backend.orchestrator.celery_app worker -l warning &
  echo $! > $CELERY_PID_FILE

  echo "🌐 Building and serving web..."
  npm --prefix web run build
  npx serve -s web/dist -l 0.0.0.0:5173 &
  echo $! > $WEB_PID_FILE

  echo "✅ Production services started (backend:8000, web:5173)"
}

stop_services() {
  echo "🛑 Stopping services..."
  kill_one() {
    local pid_file="$1"
    [[ -f "$pid_file" ]] || return 0
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      pkill -TERM -P "$pid" 2>/dev/null || true
      for i in {1..10}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.3
      done
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
        pkill -9 -P "$pid" 2>/dev/null || true
      fi
      echo "Stopped PID $pid from $pid_file"
    fi
    rm -f "$pid_file"
  }

  kill_one "$BACK_PID_FILE"
  kill_one "$CELERY_PID_FILE"
  kill_one "$WEB_PID_FILE"

  # Fallback: ensure no stragglers keep ports bound
  pkill -f "uvicorn backend.main:app" 2>/dev/null || true
  pkill -f "celery -A backend.orchestrator.celery_app worker" 2>/dev/null || true
  pkill -f "vite --host" 2>/dev/null || true
  pkill -f "serve -s web/dist" 2>/dev/null || true
  echo "✅ Services stopped."
}

case "$1" in
  start|dev)
    start_dev
    ;;
  prod)
    start_prod
    ;;
  stop)
    stop_services
    ;;
  *)
    echo "Usage: $0 {start|dev|prod|stop}"
    exit 1
    ;;
 esac 