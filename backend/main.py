from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from backend.routes import auth as auth_router
from backend.routes import orchestrator as orch_router
from backend.routes import sync_runs as runs_router
from backend.routes import profiles as profiles_router

app = FastAPI(
    title="Integration Server",
    version="0.1.0",
    description="Multi-tenant integration server that syncs documents from various sources to destinations like CleverBrag and Onyx.",
    terms_of_service="https://example.com/terms",
    contact={"name": "Dev Team", "email": "dev@example.com"},
    license_info={"name": "MIT"},
)

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


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Simple health check used by load-balancers and uptime monitors."""
    return {"status": "ok"} 