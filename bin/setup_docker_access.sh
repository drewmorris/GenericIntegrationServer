#!/usr/bin/env bash
# Idempotent setup for Docker + act inside the devcontainer
# - Ensures docker CLI is present
# - Configures DOCKER_HOST if /var/run/docker.sock is unavailable
# - Installs `act` locally to ./bin if missing
# - Pre-pulls commonly used images

set -euo pipefail

log() { echo -e "\033[1;36m$*\033[0m"; }
warn() { echo -e "\033[1;33m$*\033[0m"; }
err() { echo -e "\033[1;31m$*\033[0m"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
ENV_FILE="$ROOT_DIR/.docker_env"
# Resolve current user robustly even when $USER is unset under set -u
CURRENT_USER="${SUDO_USER:-${USER:-$(id -un)}}"

ensure_docker_cli() {
  if command -v docker >/dev/null 2>&1; then
    log "✅ docker CLI found"
    return 0
  fi
  if command -v apt-get >/dev/null 2>&1; then
    log "▶️  Installing docker.io via apt-get"
    sudo apt-get update -y >/dev/null 2>&1 || true
    sudo apt-get install -y docker.io >/dev/null 2>&1 || true
  fi
  if command -v docker >/dev/null 2>&1; then
    log "✅ docker CLI installed"
  else
    warn "⚠️  Could not install docker CLI automatically; please install it"
  fi
}

detect_docker_host() {
  # Prefer local socket
  if [[ -S /var/run/docker.sock ]]; then
    log "✅ Docker socket available at /var/run/docker.sock"
    # Check if current user can access the socket
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    warn "⚠️  Docker socket present but not accessible by user '$CURRENT_USER'"
    # Align group inside container with host socket GID and add current user
    local gid gname
    gid=$(stat -c %g /var/run/docker.sock 2>/dev/null || echo "")
    if [[ -n "$gid" ]]; then
      gname=$(getent group "$gid" | cut -d: -f1 || true)
      if [[ -z "$gname" ]]; then
        gname="dockersock"
        sudo groupadd -g "$gid" "$gname" >/dev/null 2>&1 || true
      fi
      sudo usermod -aG "$gname" "$CURRENT_USER" >/dev/null 2>&1 || true
      # Attempt to grant ACL on the socket for immediate access
      if command -v setfacl >/dev/null 2>&1; then
        sudo setfacl -m "u:$CURRENT_USER:rw" /var/run/docker.sock >/dev/null 2>&1 || true
      else
        sudo chgrp "$gname" /var/run/docker.sock >/dev/null 2>&1 || true
        sudo chmod g+rw /var/run/docker.sock >/dev/null 2>&1 || true
      fi
      if docker info >/dev/null 2>&1; then
        log "✅ Docker socket access granted for $CURRENT_USER"
        return 0
      else
        warn "ℹ️  You may need to restart the shell/devcontainer for group changes to take effect."
      fi
    fi
    # Do not return yet — fall through to TCP probing as a fallback
  fi

  # Try TCP daemon via host.docker.internal:2375 if reachable
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS --max-time 1 http://host.docker.internal:2375/_ping >/dev/null 2>&1; then
      export DOCKER_HOST="tcp://host.docker.internal:2375"
      log "✅ Detected Docker daemon on $DOCKER_HOST"
      echo "export DOCKER_HOST=$DOCKER_HOST" > "$ENV_FILE"
      return 0
    fi
  else
    # Fallback TCP probe using bash if curl is unavailable
    if (exec 3<>/dev/tcp/host.docker.internal/2375) 2>/dev/null; then
      exec 3>&- 3<&-
      export DOCKER_HOST="tcp://host.docker.internal:2375"
      log "✅ Detected Docker daemon on $DOCKER_HOST"
      echo "export DOCKER_HOST=$DOCKER_HOST" > "$ENV_FILE"
      return 0
    fi
  fi

  # Try host.docker.internal:2375
  local host_alias="host.docker.internal"
  if getent hosts "$host_alias" >/dev/null 2>&1; then
    export DOCKER_HOST="tcp://$host_alias:2375"
    if docker info >/dev/null 2>&1; then
      log "✅ Using DOCKER_HOST=$DOCKER_HOST"
      echo "export DOCKER_HOST=$DOCKER_HOST" > "$ENV_FILE"
      return 0
    fi
  fi

  # Try default gateway on port 2375 (Docker Desktop/daemon with TCP exposed)
  local gw
  gw=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
  if [[ -n "${gw:-}" ]]; then
    export DOCKER_HOST="tcp://$gw:2375"
    if docker info >/dev/null 2>&1; then
      log "✅ Using DOCKER_HOST=$DOCKER_HOST (gateway)"
      echo "export DOCKER_HOST=$DOCKER_HOST" > "$ENV_FILE"
      return 0
    fi
  fi

  warn "⚠️  Docker daemon not reachable. If using Docker Desktop, enable: 'Expose daemon on tcp://localhost:2375 without TLS'"
  warn "   Then re-run this script."
  return 1
}

ensure_act() {
  if command -v act >/dev/null 2>&1; then
    log "✅ act found in PATH"
    return 0
  fi
  log "▶️  Installing act to ./bin"
  mkdir -p "$ROOT_DIR/bin"
  if command -v curl >/dev/null 2>&1; then
    (cd "$ROOT_DIR/bin" && curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | bash >/dev/null 2>&1) || true
  fi
  if command -v act >/dev/null 2>&1; then
    log "✅ act installed"
  elif [[ -x "$ROOT_DIR/bin/act" ]]; then
    export PATH="$ROOT_DIR/bin:$PATH"
    log "✅ act installed to ./bin (PATH updated for current shell)"
  else
    warn "⚠️  act install script did not succeed; download manually from https://github.com/nektos/act/releases"
  fi
}

prepull_images() {
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  log "▶️  Pre-pulling useful images"
  docker pull ghcr.io/catthehacker/ubuntu:act-latest >/dev/null 2>&1 || true
  docker pull postgres:15-alpine >/dev/null 2>&1 || true
  docker pull redis:7-alpine >/dev/null 2>&1 || true
}

summary() {
  echo ""
  echo "================== Docker/act Setup =================="
  if [[ -f "$ENV_FILE" ]]; then
    echo "Environment written to $ENV_FILE"
    echo "To persist in your shell:"
    echo "  source $ENV_FILE"
  fi
  echo "Docker info:"
  if command -v docker >/dev/null 2>&1; then
    docker info -f '{{.ServerVersion}}' 2>/dev/null || true
  fi
  echo "act: $(command -v act >/dev/null 2>&1 && act --version || echo 'not installed')"
}

main() {
  ensure_docker_cli
  detect_docker_host || true
  ensure_act
  prepull_images
  summary
}

main "$@"


