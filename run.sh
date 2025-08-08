#!/usr/bin/env bash

# Simple dev convenience script to start/stop backend, worker and web dev server.
# Usage: ./run.sh start   – start all processes
#        ./run.sh stop    – stop all previously started processes

BACK_PID_FILE=.backend.pid
CELERY_PID_FILE=.celery.pid
WEB_PID_FILE=.web.pid

start_dev() {
  echo "🚀 Starting backend (uvicorn)..."
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
  echo $! > $BACK_PID_FILE

  echo "🧵 Starting Celery worker..."
  celery -A backend.orchestrator.celery_app worker -l info &
  echo $! > $CELERY_PID_FILE

  echo "🌐 Starting web dev server..."
  npm --prefix web run dev -- --port 5173 &
  echo $! > $WEB_PID_FILE

  echo "✅ All services started (backend:8000, web:5173)"
}

start_prod() {
  echo "🚀 Starting backend (gunicorn)..."
  gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 &
  echo $! > $BACK_PID_FILE

  echo "🧵 Starting Celery worker (prod)..."
  celery -A backend.orchestrator.celery_app worker -l warning &
  echo $! > $CELERY_PID_FILE

  echo "🌐 Building and serving web..."
  npm --prefix web run build
  npx serve -s web/dist -l 5173 &
  echo $! > $WEB_PID_FILE

  echo "✅ Production services started (backend:8000, web:5173)"
}

stop_services() {
  echo "🛑 Stopping services..."
  for f in $BACK_PID_FILE $CELERY_PID_FILE $WEB_PID_FILE; do
    if [[ -f $f ]]; then
      pid=$(cat $f)
      if kill -0 $pid 2>/dev/null; then
        kill $pid && echo "Stopped PID $pid from $f"
      fi
      rm -f $f
    fi
  done
  echo "✅ Services stopped."
}

case "$1" in
  dev)
    start_dev
    ;;
  prod)
    start_prod
    ;;
  stop)
    stop_services
    ;;
  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;
 esac 