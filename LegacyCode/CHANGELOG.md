## [Unreleased] – 2025-07-31
### Added
- VS Code Dev Container support via `.devcontainer/devcontainer.json` with Docker Compose integration for local development. 
- Added `TODO_R2R_Integration` file containing full execution plan for new Integration Server with multi-tenancy and R2R integration. 
- Added `scripts/copy_to_new_integration_server.ps1` PowerShell script to copy connector runtime and dependencies into `NewIntegrationServer`. 
### Fixed
- Replaced unsupported `--no-require-hashes` flag with `PIP_REQUIRE_HASHES=0` environment variable in backend Dockerfile to bypass hash verification. 
### Changed
- Exposed Postgres `relational_db` on host port 5433 instead of unbound (allows local Postgres to coexist while still enabling external connections). 
### Fixed
- Changed Dev Container `workspaceFolder` and mount to `/app` so VS Code no longer errors "workspace does not exist" when attaching. 
- Removed macOS-only ':cached' mount option from Dev Container bind mounts to avoid unnecessary warnings and improve cross-platform performance.
- Commented out Docker `build:` blocks in `deployment/docker_compose/docker-compose.dev.yml` (api_server, background, web_server, inference_model_server, indexing_model_server) so dev-container start skips time-consuming image builds. 
- Limited Dev Container `runServices` to `relational_db`, `cache`, `api_server`, and `web_server` only, preventing memory exhaustion during VS Code attach. 
- Overrode `api_server` dependencies in `.devcontainer/docker-compose.override.yml` so only `relational_db` and `cache` start (no Vespa / model-servers / MinIO), preventing forced startup of high-memory containers. 
- Fixed missing `alembic.ini` crash: bind-mounts now map `../backend` to `/app` (api_server, background) and `../web` to `/app` (web_server) so migrations and Next.js assets are found inside containers. 
- Replaced `api_server` depends_on with empty list to fully remove automatic startup of heavy services in dev container. 
- Mount fix alone was sufficient; reverted `working_dir` override for `api_server` and `background` to default path after encountering Python path error. 
- Changed devcontainer to mount workspace at `/workspace` instead of `/app` (using default VS Code automatic mount, removed manual `workspaceMount`). 
- Refined lightweight stack: override now nulls out heavy dependencies (`index`, `minio`, `*-model_server`) under `depends_on`, leaving only `relational_db` and `cache`. Compose no longer starts the heavyweight containers during dev-container attach. 
- Added `.devcontainer/docker-compose.light.yml` and pointed devcontainer to it; this file re-defines only the lightweight services so heavy components are never started during development. 
- Switched dev-container to use only `docker-compose.light.yml`, a standalone file that defines just Postgres, Redis, backend, worker, web, and nginx. Heavy services are no longer referenced, eliminating validation errors and memory drain. 
- Restored explicit `workspaceMount` to bind host repo into `/workspaces/onyx` after automatic mount proved unreliable, restoring Explorer visibility. 