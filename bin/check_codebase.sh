#!/usr/bin/env bash
# Comprehensive code-quality script.
# Usage:
#   bin/check_codebase.sh                 # interactive menu (default)
#   bin/check_codebase.sh --ci            # non-interactive, run everything & fail on error
#   bin/check_codebase.sh --ci-emulate    # emulate CI locally (dockerized PG/Redis, schema reset, isolated env)
#   bin/check_codebase.sh --gh            # run GitHub workflow locally via `act -j build`
#   bin/check_codebase.sh --keep-containers  # preserve containers between runs (faster subsequent runs)
#   bin/check_codebase.sh --no-web-checks    # skip web-related checks (frontend linting, tests, build)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

mkdir -p "$ROOT_DIR/logs"

# Defaults
CI_EMULATE=false
RUN_GH=false
DOCKER_AVAILABLE=false
NO_WEB_CHECKS=false
KEEP_CONTAINERS=false
PYTEST_CMD="poetry run pytest -q"

# Parse flags
for arg in "$@"; do
  case "$arg" in
    --ci-emulate)
      CI_EMULATE=true
      ;;
    --gh)
      RUN_GH=true
      ;;
    --no-web-checks)
      NO_WEB_CHECKS=true
      ;;
    --keep-containers)
      KEEP_CONTAINERS=true
      ;;
  esac
done

# Helper: log
log() { echo -e "\033[1;36m$*\033[0m"; }

# Ensure Docker/act access if needed
if [[ "$RUN_GH" == true || "$CI_EMULATE" == true ]]; then
  if [[ -x "$ROOT_DIR/bin/setup_docker_access.sh" ]]; then
    bash "$ROOT_DIR/bin/setup_docker_access.sh" || true
    if [[ -f "$ROOT_DIR/.docker_env" ]]; then
      # shellcheck disable=SC1091
      source "$ROOT_DIR/.docker_env"
    fi
  fi
fi

# When planning to run GitHub Actions locally via --gh, only run unit tests here
if [[ "$RUN_GH" == true ]]; then
  PYTEST_CMD="poetry run pytest -q -k 'not integration'"
fi

# Detect Poetry availability and prepare environment if missing
POETRY_AVAILABLE=false
if command -v poetry >/dev/null 2>&1; then
  POETRY_AVAILABLE=true
else
  log "ℹ️  Poetry not found; falling back to system Python environment"
  if [[ -f requirements/default.txt ]]; then
    log "▶️  Ensuring base Python dependencies are installed"
    pip install -q -r requirements/default.txt || true
  fi
  if [[ -f requirements/dev.txt ]]; then
    log "▶️  Ensuring dev tools (ruff, mypy, pytest) are installed"
    pip install -q -r requirements/dev.txt || true
  fi
fi

# Helper: run alembic programmatically with provided URL
alembic_upgrade_with_url() {
  local url="$1"
  python - <<PY
from alembic.config import Config
from alembic import command
cfg = Config("backend/alembic.ini")
cfg.set_main_option("sqlalchemy.url", "$url")
command.upgrade(cfg, "head")
print("Alembic upgrade head OK →", "$url")
PY
}

# Helper: reset database schema (faster than recreating container)
reset_database_schema() {
  local url="$1"
  log "🔄 Resetting database schema (faster than container recreation)"
  python - <<PY
from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from sqlalchemy import text

url = "$url"
cfg = Config("backend/alembic.ini")
cfg.set_main_option("sqlalchemy.url", url)

try:
    # Drop all tables by downgrading to base, then upgrade to head
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    print("✅ Database schema reset complete")
except Exception as e:
    print(f"⚠️  Schema reset failed: {e}")
    # Fallback: try to drop all tables manually
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename != 'alembic_version'
        """))
        tables = [row[0] for row in result]
        
        if tables:
            # Drop all tables
            conn.execute(text(f"DROP TABLE IF EXISTS {', '.join(tables)} CASCADE"))
            conn.commit()
            print(f"🗑️  Dropped {len(tables)} tables manually")
        
        # Re-run migrations
        command.upgrade(cfg, "head")
        print("✅ Database schema recreated")
PY
}

# Optional CI emulation prelude
if [[ "$CI_EMULATE" == true ]]; then
  log "▶️  CI emulation: verifying Docker"
  if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
    log "🐳 Docker available; pre-pulling images"
    docker pull postgres:15-alpine >/dev/null || true
    docker pull redis:7-alpine >/dev/null || true

    # Start persistent Postgres on host 5432 if not already running
    PG_CONT_NAME="gis_ci_pg_persistent"
    REDIS_CONT_NAME="gis_ci_redis_persistent"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      # Check if container exists but is stopped
      if docker ps -a --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
        log "▶️  Restarting existing Postgres container ${PG_CONT_NAME}"
        docker start "$PG_CONT_NAME" >/dev/null
      else
        log "▶️  Creating new persistent Postgres container ${PG_CONT_NAME} on 5432"
        docker run -d --name "$PG_CONT_NAME" \
          -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
          -e POSTGRES_DB=integration_server -p 5432:5432 postgres:15-alpine >/dev/null
      fi
    else
      log "✅ Postgres container ${PG_CONT_NAME} already running"
    fi
    
    # Start persistent Redis if not already running
    if ! docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
      if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONT_NAME}$"; then
        log "▶️  Restarting existing Redis container ${REDIS_CONT_NAME}"
        docker start "$REDIS_CONT_NAME" >/dev/null
      else
        log "▶️  Creating new persistent Redis container ${REDIS_CONT_NAME} on 6379"
        docker run -d --name "$REDIS_CONT_NAME" -p 6379:6379 redis:7-alpine >/dev/null
      fi
    else
      log "✅ Redis container ${REDIS_CONT_NAME} already running"
    fi
    
    # Wait until Postgres is ready
    log "⏳ Waiting for Postgres to be ready"
    for i in {1..30}; do
      if docker exec "$PG_CONT_NAME" pg_isready -U postgres >/dev/null 2>&1; then break; fi
      sleep 1
    done

    # Determine reachable host for published port from inside container
    PG_HOST_CANDIDATE="host.docker.internal"
    # Test connectivity using python socket to avoid nc dependency
    python - <<'PY' || PG_HOST_CANDIDATE="127.0.0.1"
import socket, sys
host = "host.docker.internal"; port = 5432
s = socket.socket(); s.settimeout(0.5)
try:
    s.connect((host, port))
    print("ok")
except Exception:
    sys.exit(1)
finally:
    try: s.close()
    except Exception: pass
PY

    # Reset database schema for clean test environment
    DB_URL="postgresql://postgres:postgres@${PG_HOST_CANDIDATE}:5432/integration_server"
    if reset_database_schema "$DB_URL"; then
      export CI_EMULATED_POSTGRES=1
      export CI_PG_HOST="$PG_HOST_CANDIDATE" CI_PG_PORT=5432 CI_PG_USER=postgres CI_PG_PASSWORD=postgres CI_PG_DB=integration_server
      export REDIS_HOST="$PG_HOST_CANDIDATE" REDIS_PORT=6379
      log "✅ Database and Redis ready for testing"
    else
      log "⚠️  Database schema reset failed; proceeding without isolated pytest env"
    fi
  else
    log "⚠️  Docker not available; running CI emulation without dockerized services"
    log "    Integration tests that require Docker will self-skip; continuing"
  fi
fi

commands=(
  "poetry run ruff check ." 
  "poetry run mypy backend" 
  "$PYTEST_CMD" 
  "command -v npm >/dev/null && npm --prefix web run format:check --silent" 
  "command -v npm >/dev/null && npm --prefix web run lint -- --max-warnings=0" 
  "command -v npm >/dev/null && npm --prefix web run test -- --run --silent" 
  "command -v npm >/dev/null && npm --prefix web run build"
)

labels=(
  "Ruff Lint (Python)" 
  "Mypy Type Check" 
  "Backend Pytests" 
  "Prettier Format Check (Web)" 
  "ESLint (Web)" 
  "Web Unit Tests" 
  "Web Build"
)

# Show interactive menu unless --ci supplied
if [[ "${1:-}" != "--ci" && "$CI_EMULATE" != true && "$RUN_GH" != true ]]; then
  echo "🔧 Available Steps:"
  for idx in "${!labels[@]}"; do
    printf "%2d) %s\n" "$((idx+1))" "${labels[$idx]}"
  done
  echo -e "\na) Run all"
  echo -e "f) Run fix commands"
  read -rp "👉 Choose steps (e.g. 1 3 5 or 'a'): " choice
  if [[ "$choice" == "a" ]]; then
    selected_indices=( $(seq 0 $((${#commands[@]}-1))) )
  elif [[ "$choice" == "f" ]]; then
    # Show fix sub-menu
    fix_cmds=(
      "ruff check --fix ." 
      "command -v npm >/dev/null && npm --prefix web run format --silent" 
      "command -v npm >/dev/null && npm --prefix web run lint -- --fix"
    )
    fix_labels=(
      "Ruff Auto-fix (Python)" 
      "Prettier Format (Web)" 
      "ESLint --fix (Web)"
    )

    echo -e "\n🔧 Available Fixes:"
    for idx in "${!fix_labels[@]}"; do
      printf "%2d) %s\n" "$((idx+1))" "${fix_labels[$idx]}"
    done
    echo -e "\na) Run all fixes\n"
    read -rp "👉 Choose fixes (e.g. 1 2 or 'a'): " fix_choice
    if [[ "$fix_choice" == "a" ]]; then
      selected_fix_indices=( $(seq 0 $((${#fix_cmds[@]}-1))) )
    else
      read -ra num <<< "$fix_choice"
      selected_fix_indices=()
      for n in "${num[@]}"; do
        selected_fix_indices+=( $((n-1)) )
      done
    fi

    # Execute selected fixes directly and exit
    for i in "${selected_fix_indices[@]}"; do
      lbl="${fix_labels[$i]}"
      cmd="${fix_cmds[$i]}"
      echo -e "\n🔧 Running $lbl"
      echo "   → $cmd"
      bash -c "$cmd"
    done
    echo -e "\n🏁 Fix commands completed"
    exit 0
  else
    read -ra num <<< "$choice"
    selected_indices=()
    for n in "${num[@]}"; do
      selected_indices+=( $((n-1)) )
    done
  fi
else
  selected_indices=( $(seq 0 $((${#commands[@]}-1))) )
  echo "▶️  Running all steps in CI mode (non-interactive)"
fi

# Optionally filter out web checks
if [[ "$NO_WEB_CHECKS" == true ]]; then
  echo "🧪 Skipping web checks due to --no-web-checks"
  filtered_indices=()
  for i in "${selected_indices[@]}"; do
    lbl="${labels[$i]}"
    if [[ "$lbl" == *"(Web)"* || "$lbl" == Web* ]]; then
      continue
    fi
    filtered_indices+=("$i")
  done
  selected_indices=("${filtered_indices[@]}")
fi

# Helper: try to set DOCKER_HOST when socket is absent
resolve_docker_host() {
  if [[ -z "${DOCKER_HOST:-}" && ! -S /var/run/docker.sock ]]; then
    # Prefer Docker Desktop host alias
    export DOCKER_HOST=tcp://host.docker.internal:2375
    # Fallback: try common gateway (Linux)
    if ! docker info >/dev/null 2>&1; then
      gw=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
      if [[ -n "$gw" ]]; then
        export DOCKER_HOST=tcp://$gw:2375
      fi
    fi
  fi
}

# Helper: ensure act is installed (to ./bin) and on PATH
ensure_act() {
  if ! command -v act >/dev/null; then
    log "ℹ️  'act' not found; attempting local install to ./bin"
    mkdir -p "$ROOT_DIR/bin"
    if command -v curl >/dev/null; then
      if curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | bash >/dev/null 2>&1; then
        export PATH="$ROOT_DIR/bin:$PATH"
        if command -v act >/dev/null; then
          log "✅ Installed act to ./bin and updated PATH"
        else
          log "⚠️  act install script ran but 'act' still not found; please install manually"
        fi
      else
        log "⚠️  Failed to download/install act; please install manually"
      fi
    else
      log "⚠️  curl not available; please install 'act' manually"
    fi
  fi
}

# Detect Docker availability regardless of flags
resolve_docker_host
if command -v docker >/dev/null; then
  if docker info >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
  elif [[ -n "${DOCKER_HOST:-}" ]]; then
    # If DOCKER_HOST is set, assume available and let downstream commands validate
    DOCKER_AVAILABLE=true
  fi
fi

# Run selected commands
results=()
for i in "${selected_indices[@]}"; do
  label="${labels[$i]}"
  cmd="${commands[$i]}"
  # Replace 'poetry run' prefix when Poetry is unavailable
  if [[ "$POETRY_AVAILABLE" != true ]]; then
    cmd="${cmd//poetry run /}"
  fi
  log="logs/step_${i}_${label// /_}.log"
  echo -e "\n🔄 $label"
  echo "   → $cmd"
  echo "   → log: $log"

  set +e
  if [[ "$CI_EMULATE" == true && "$label" == "Backend Pytests" && "$DOCKER_AVAILABLE" == true ]]; then
    # Run tests in an isolated environment closer to CI
    echo "   → running with env isolation"
    env -i PATH="$PATH" HOME="$HOME" \
      POSTGRES_HOST="$CI_PG_HOST" POSTGRES_PORT="$CI_PG_PORT" \
      POSTGRES_USER="$CI_PG_USER" POSTGRES_PASSWORD="$CI_PG_PASSWORD" \
      POSTGRES_DB="$CI_PG_DB" PYTHONWARNINGS=error \
      bash -lc "$cmd" 2>&1 | tee "$log"
  else
    bash -c "$cmd" 2>&1 | tee "$log"
  fi
  status=$?
  set -e

# record status
  if [[ $status -ne 0 ]]; then
    step_status="❌ FAILED"
  else
    step_status="✅ PASSED"
  fi
  results+=("$label|$step_status|$status|$log")
  echo "$step_status"
done

# Optional: run GitHub Actions workflow locally, but only if all previous steps passed
if [[ "$RUN_GH" == true ]]; then
  any_failed=0
  for entry in "${results[@]}"; do
    IFS='|' read -r _ _ code _ <<< "$entry"
    if [[ $code -ne 0 ]]; then any_failed=1; break; fi
  done
  if [[ $any_failed -eq 1 ]]; then
    log "⏭️  Skipping --gh run because one or more previous steps failed"
  else
    ensure_act
    if command -v act >/dev/null; then
      if [[ "$DOCKER_AVAILABLE" == true ]]; then
        log "▶️  Running GitHub Actions job locally (act)"
        if [[ -f .actrc ]]; then
          act -j build | tee logs/act_build.log || true
        else
          act -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest \
            --container-options "--add-host host.docker.internal:host-gateway" \
            -j build | tee logs/act_build.log || true
        fi
      else
        log "⚠️  Docker not available; skipping --gh run (act requires Docker)"
      fi
    else
      echo "act not installed; skipping --gh run"
    fi
  fi
fi

# Cleanup CI emulation resources
if [[ "$CI_EMULATE" == true && "$DOCKER_AVAILABLE" == true && "$KEEP_CONTAINERS" != true ]]; then
  log "🧹 Stopping CI containers (use --keep-containers to preserve them)"
  docker stop "$PG_CONT_NAME" "$REDIS_CONT_NAME" >/dev/null 2>&1 || true
elif [[ "$CI_EMULATE" == true && "$DOCKER_AVAILABLE" == true && "$KEEP_CONTAINERS" == true ]]; then
  log "🔄 Keeping containers running for next run (${PG_CONT_NAME}, ${REDIS_CONT_NAME})"
  log "   To stop them manually: docker stop ${PG_CONT_NAME} ${REDIS_CONT_NAME}"
fi

# summary
echo -e "\n================== Summary =================="
failures=0
for entry in "${results[@]}"; do
  IFS='|' read -r lbl stat code logfile <<< "$entry"
  printf "%s — %s (exit %s, log: %s)\n" "$lbl" "$stat" "$code" "$logfile"
  if [[ $code -ne 0 ]]; then failures=1; fi
done

if [[ $failures -ne 0 ]]; then
  echo "🚨 Some steps failed. See logs above."
  exit 1
else
  echo "🏁 All selected steps completed successfully"
fi


