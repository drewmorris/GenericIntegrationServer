# Docker/WSL2 EIO Error Fixes

## The Problem
EIO (Input/Output) errors occur when Docker containers running on WSL2 have filesystem sync issues with the Windows host.

## Immediate Workarounds

### 1. Use the Simplified Startup Script
```bash
./simple_start.sh
```
This avoids npm/node_modules operations that commonly trigger EIO errors.

### 2. Clear Docker Cache
```bash
docker system prune -af
docker volume prune -f
```

### 3. Restart Docker Desktop
- Right-click Docker Desktop → Quit
- Wait 10 seconds
- Restart Docker Desktop

## WSL2 Fixes

### 1. Increase WSL2 Memory Limit
Create/edit `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
```

### 2. Restart WSL2
```cmd
wsl --shutdown
wsl --distribution Ubuntu
```

### 3. Move Project to Linux Filesystem
Instead of `/workspaces` (Windows mount), use:
```bash
cp -r /workspaces/GenericIntegrationServer ~/GenericIntegrationServer
cd ~/GenericIntegrationServer
```

## Docker Desktop Settings

1. **Settings → General**:
   - ✅ Use WSL 2 based engine

2. **Settings → Resources → WSL Integration**:
   - ✅ Enable integration with default WSL distro
   - ✅ Enable integration with your Ubuntu distro

3. **Settings → Docker Engine**:
   Add to configuration:
   ```json
   {
     "storage-driver": "overlay2",
     "log-driver": "local",
     "log-opts": {
       "max-size": "10m",
       "max-file": "3"
     }
   }
   ```

## Alternative: Use Linux-Native Development

For persistent issues, consider:
1. Run directly in a Linux VM
2. Use GitHub Codespaces
3. Use Docker on a Linux host

## Test the Fix
```bash
./simple_start.sh
curl http://localhost:8000/health
```









