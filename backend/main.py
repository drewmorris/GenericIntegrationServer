from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from backend.routes import auth as auth_router

app = FastAPI(title="Integration Server", version="0.1.0")

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

app.include_router(auth_router.router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Simple health check used by load-balancers and uptime monitors."""
    return {"status": "ok"} 