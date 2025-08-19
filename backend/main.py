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
from backend.logging import configure_logging
from backend.db.startup import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    initialize_database()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Integration Server",
    version="0.1.0",
    description="Multi-tenant integration server that syncs documents from various sources to destinations like CleverBrag and Onyx.",
    terms_of_service="https://example.com/terms",
    contact={"name": "Dev Team", "email": "dev@example.com"},
    license_info={"name": "MIT"},
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


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Simple health check used by load-balancers and uptime monitors."""
    return {"status": "ok"} 