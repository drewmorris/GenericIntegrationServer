from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from backend.routes import auth as auth_router
from backend.routes import orchestrator as orch_router
from backend.routes import sync_runs as runs_router
from backend.routes import profiles as profiles_router
from backend.routes import destinations as destinations_router
from backend.routes import targets as targets_router
from backend.routes import connectors as connectors_router
from backend.routes import credentials as credentials_router
from backend.routes import oauth as oauth_router
from backend.routes import google_oauth as google_oauth_router
from backend.routes import security as security_router
from backend.routes import api_keys as api_keys_router
from backend.routes import cc_pairs as cc_pairs_router
from backend.routes import migration as migration_router
from backend.routes import health as health_router
from backend.routes import metrics as metrics_router
from backend.routes import alerts as alerts_router
from backend.routes import users as users_router
from backend.log_config import configure_logging
from backend.db.startup import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    initialize_database()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Generic Integration Server",
    version="1.6.3",
    description="""
    **Multi-tenant Integration Server** for syncing data from 80+ connectors to multiple destinations.
    
    ## Features
    
    * **83+ Connectors**: Google Drive, Slack, Confluence, GitHub, and more
    * **Multi-tenant**: Organization-based isolation with Row-Level Security  
    * **Flexible Destinations**: CleverBrag, Onyx, CSV, and extensible plugin system
    * **Advanced Security**: Encrypted credentials, API keys, audit logging
    * **Real-time Monitoring**: Prometheus metrics, Grafana dashboards, intelligent alerting
    * **CC-Pair Architecture**: Flexible connector-credential pairing for enterprise deployments
    
    ## Authentication
    
    This API supports two authentication methods:
    * **JWT Bearer Tokens**: For web applications (obtain via `/auth/login`)
    * **API Keys**: For programmatic access (create via `/api-keys/`)
    
    ## Key Concepts
    
    * **Connectors**: Reusable configurations for data sources (Google Drive, Slack, etc.)
    * **Credentials**: Encrypted authentication data (OAuth tokens, API keys)
    * **CC-Pairs**: Connector-Credential Pairs that define sync relationships  
    * **Destinations**: Target systems where synced data is sent
    * **Index Attempts**: Detailed sync operation tracking with progress monitoring
    """,
    terms_of_service="https://github.com/your-org/integration-server/blob/main/TERMS.md",
    contact={"name": "Integration Server Team", "email": "support@yourcompany.com", "url": "https://github.com/your-org/integration-server"},
    license_info={"name": "MIT", "url": "https://github.com/your-org/integration-server/blob/main/LICENSE"},
    lifespan=lifespan,
)

configure_logging()

# CORS for local dev UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

app.include_router(auth_router.router)
app.include_router(orch_router.router)
app.include_router(runs_router.router)
app.include_router(profiles_router.router)
app.include_router(destinations_router.router)
app.include_router(targets_router.router)
app.include_router(connectors_router.router)
app.include_router(credentials_router.router)
app.include_router(oauth_router.router)
app.include_router(google_oauth_router.router)
app.include_router(security_router.router)
app.include_router(api_keys_router.router)
app.include_router(cc_pairs_router.router)
app.include_router(migration_router.router)
app.include_router(health_router.router)
app.include_router(metrics_router.router)
app.include_router(alerts_router.router)
app.include_router(users_router.router)


@app.get("/health", tags=["Health"])
async def simple_health() -> dict[str, str]:
    """Simple health check used by load-balancers and uptime monitors (no database dependency)."""
    return {"status": "ok"} 