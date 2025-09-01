#!/usr/bin/env bash
# Setup pnpm for the current environment

set -euo pipefail

log() { echo -e "\033[1;36m[$(date '+%H:%M:%S')] $*\033[0m"; }
success() { echo -e "\033[1;32m[$(date '+%H:%M:%S')] ✅ $*\033[0m"; }
error() { echo -e "\033[1;31m[$(date '+%H:%M:%S')] ❌ $*\033[0m"; }

log "🚀 Setting up pnpm environment..."

# Install pnpm if not available
if ! command -v pnpm >/dev/null 2>&1; then
    log "Installing pnpm..."
    curl -fsSL https://get.pnpm.io/install.sh | sh -
    export PNPM_HOME="$HOME/.local/share/pnpm"
    export PATH="$PNPM_HOME:$PATH"
    success "pnpm installed"
else
    success "pnpm already available"
fi

# Ensure pnpm is in PATH
export PNPM_HOME="$HOME/.local/share/pnpm"
export PATH="$PNPM_HOME:$PATH"

log "pnpm version: $(pnpm --version)"

# Install frontend dependencies
log "Installing frontend dependencies..."
cd web
pnpm install --no-verify-store-integrity --fetch-timeout 100000

if [[ $? -eq 0 ]]; then
    success "Frontend dependencies installed successfully!"
    log "Testing frontend build..."
    if pnpm run build; then
        success "Frontend build successful!"
    else
        error "Frontend build failed"
    fi
else
    error "Frontend dependency installation failed"
fi







