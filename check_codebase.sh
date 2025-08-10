#!/usr/bin/env bash
# Comprehensive code-quality script.
# Usage:
#   ./check_codebase.sh                 # interactive menu (default)
#   ./check_codebase.sh --ci            # non-interactive, run everything & fail on error
#   ./check_codebase.sh --ci-emulate    # emulate CI locally (dockerized PG, alembic smoke, isolated env)
#   ./check_codebase.sh --gh            # run GitHub workflow locally via `act -j build`

set -euo pipefail

mkdir -p logs

# Defaults
CI_EMULATE=false
RUN_GH=false
DOCKER_AVAILABLE=false

# Parse flags
for arg in "$@"; do
  case "$arg" in
    --ci-emulate)
      CI_EMULATE=true
      ;;
    --gh)
      RUN_GH=true
      ;;
  esac
done

# Helper: log
log() { echo -e "\033[1;36m$*\033[0m"; }

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

# Optional CI emulation prelude
if [[ "$CI_EMULATE" == true ]]; then
  log "▶️  CI emulation: verifying Docker"
  if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
    log "🐳 Docker available; pre-pulling images"
    docker pull postgres:15-alpine >/dev/null || true
    docker pull redis:7-alpine >/dev/null || true

    # Start throwaway Postgres on host 5432 if not already bound
    PG_CONT_NAME="gis_ci_pg"
    if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONT_NAME}$"; then
      log "▶️  Starting Postgres container ${PG_CONT_NAME} on 5432"
      docker run --rm -d --name "$PG_CONT_NAME" \
        -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=integration_server -p 5432:5432 postgres:15-alpine >/dev/null
    fi
    # Wait until ready
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

    # Try Alembic smoke against detected host; if it fails, continue gracefully
    if python - <<PY
from alembic.config import Config
from alembic import command
url = f"postgresql://postgres:postgres@${PG_HOST_CANDIDATE}:5432/integration_server"
try:
    cfg = Config("backend/alembic.ini"); cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head"); print("Alembic upgrade head OK →", url)
except Exception as e:
    import sys; print("Alembic smoke failed:", e); sys.exit(1)
PY
    then
      export CI_EMULATED_POSTGRES=1
      export CI_PG_HOST="$PG_HOST_CANDIDATE" CI_PG_PORT=5432 CI_PG_USER=postgres CI_PG_PASSWORD=postgres CI_PG_DB=integration_server
    else
      log "⚠️  Alembic smoke migration failed; proceeding without isolated pytest env"
    fi
  else
    log "⚠️  Docker not available; running CI emulation without dockerized services"
    log "    Integration tests that require Docker will self-skip; continuing"
  fi
fi

commands=(
  "poetry run ruff check ." 
  "poetry run mypy backend" 
  "poetry run pytest -q" 
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


# Run selected commands
results=()
for i in "${selected_indices[@]}"; do
  label="${labels[$i]}"
  cmd="${commands[$i]}"
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

# Optional: run GitHub Actions workflow locally
if [[ "$RUN_GH" == true ]]; then
  if command -v act >/dev/null; then
    if [[ "$DOCKER_AVAILABLE" == true ]]; then
      log "▶️  Running GitHub Actions job locally (act)"
      act -j build --container-privileged | tee logs/act_build.log || true
    else
      log "⚠️  Docker not available; skipping --gh run (act requires Docker)"
    fi
  else
    echo "act not installed; skipping --gh run"
  fi
fi

# Cleanup CI emulation resources
if [[ "$CI_EMULATE" == true && "$DOCKER_AVAILABLE" == true ]]; then
  log "🧹 Stopping CI Postgres container"
  docker stop "$PG_CONT_NAME" >/dev/null || true
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
