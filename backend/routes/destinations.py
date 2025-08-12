from __future__ import annotations

from fastapi import APIRouter

from backend.destinations import registry

router = APIRouter(prefix="/destinations", tags=["Destinations"])

@router.get(
    "/definitions",
    summary="List available destination definitions",
    description="Returns destination names and their configuration schemas for building UI forms.",
)
async def list_destination_definitions() -> list[dict]:
    defs = []
    for name, cls in registry.items():
        inst = cls()
        schema = inst.config_schema()
        defs.append({"name": name, "schema": schema})
    return defs 