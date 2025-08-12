from __future__ import annotations

from fastapi import APIRouter

from connectors.onyx.configs.constants import DocumentSource

router = APIRouter(prefix="/connectors", tags=["Connectors"])


def _titleize(name: str) -> str:
    return name.replace('_', ' ').title()


@router.get(
    "/definitions",
    summary="List available connector definitions",
    description="Returns connector names and minimal configuration schemas for building UI forms.",
)
async def list_connector_definitions() -> list[dict]:
    defs: list[dict] = []
    # Add mock first for demos
    defs.append(
        {
            "name": "mock_source",  # internal alias used by our UI and orchestrator
            "schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Mock Source",
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
    )

    # Enumerate Onyx DocumentSource entries (excluding special cases)
    exclude = {DocumentSource.INGESTION_API, DocumentSource.NOT_APPLICABLE, DocumentSource.MOCK_CONNECTOR}
    for src in DocumentSource:
        if src in exclude:
            continue
        name = src.value
        defs.append(
            {
                "name": name,
                "schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "title": _titleize(name),
                    "type": "object",
                    # MVP: leave properties empty; connectors typically pull credentials separately
                    "properties": {},
                    "required": [],
                },
            }
        )
    return defs 