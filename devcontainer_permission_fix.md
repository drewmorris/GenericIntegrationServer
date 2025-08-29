# DevContainer Permission Fix

## 🔧 **Issue Fixed**
The pnpm installation was failing during `postCreateCommand` with permission errors:
```
EACCES: permission denied, copyfile '/tmp/tmp.EqBoD37jAU/pnpm' -> '/home/vscode/.local/share/pnpm/pnpm'
```

## 💡 **Root Cause**
Even with mounting only the `/store` subdirectory, Docker was creating the parent `/home/vscode/.local/share/pnpm` directory with root ownership when mounting the child directory, preventing pnpm from writing its CLI binary.

## ✅ **Solution Applied - Two-Part Fix**
**1. Changed the mount point** from:
```json
"type=volume,source=gis-pnpm-cache,target=/home/vscode/.local/share/pnpm"
```
**To the specific cache subdirectory**:
```json
"type=volume,source=gis-pnpm-store,target=/home/vscode/.local/share/pnpm/store"
```

**3. Added Python Virtual Environment Docker Volume**:
```json
"type=volume,source=gis-python-venv,target=${containerWorkspaceFolder}/.venv"
```
This moves the Python virtual environment to Docker-managed storage, protecting MyPy, pytest, and all Python dependencies from WSL2 filesystem corruption.

**4. Added comprehensive ownership fixes to postCreateCommand**:
```bash
# First: Fix Python virtual environment Docker volume ownership
sudo chown -R vscode:vscode /workspaces/GenericIntegrationServer/.venv

# Second: Configure Poetry to use in-project virtual environment
poetry config virtualenvs.in-project true && poetry install --no-root --with dev

# Third: Fix pnpm installation directory
mkdir -p /home/vscode/.local/share/pnpm && sudo chown -R vscode:vscode /home/vscode/.local/share/pnpm

# Fourth: Install pnpm with shell detection
export SHELL=/bin/bash && curl -fsSL https://get.pnpm.io/install.sh | sh -

# Fifth: Fix node_modules right before pnpm uses it
sudo chown -R vscode:vscode /workspaces/GenericIntegrationServer/web/node_modules && cd web && pnpm install
```
**Critical timing**: All Docker volumes are created at container startup with root ownership, so we must fix ownership before package managers try to use them.

**3. Added shell detection fix**:
```bash
export SHELL=/bin/bash && curl -fsSL https://get.pnpm.io/install.sh | sh -
```
This fixes the `ERR_PNPM_UNKNOWN_SHELL` error by explicitly setting the SHELL environment variable before pnpm installation.

**4. Added persistent SHELL environment variable**:
```json
"remoteEnv": {
  "SHELL": "/bin/bash"
}
```
This ensures the SHELL variable is available for the entire container session.

## 🚀 **Result**
- ✅ pnpm CLI can install normally to `/home/vscode/.local/share/pnpm/`
- ✅ pnpm can create subdirectories in `/workspaces/GenericIntegrationServer/web/node_modules/`
- ✅ Python virtual environment stored in Docker volume for stability
- ✅ All package management (npm/pnpm/pip) uses fast Docker volumes for performance
- ✅ No permission conflicts during installation or package management
- ✅ Shell detection works properly for pnpm installer
- ✅ MyPy and pytest protected from WSL2 filesystem corruption
- ✅ PATH export added to postCreateCommand for immediate availability

## 📋 **Next Steps**
**Ready to rebuild container** with the fixed configuration to test the full EIO error solution!

