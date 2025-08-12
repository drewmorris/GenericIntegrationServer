from __future__ import annotations

from fastapi import APIRouter

from connectors.onyx.configs.constants import DocumentSource

router = APIRouter(prefix="/connectors", tags=["Connectors"])


def _titleize(name: str) -> str:
    return name.replace('_', ' ').title()


# Hand-authored JSON Schemas for high-priority connectors (extend as needed)
RICH_SCHEMAS: dict[str, dict] = {
    "google_drive": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Google Drive",
        "type": "object",
        "properties": {
            "auth_method": {"type": "string", "enum": ["oauth", "service_account"], "default": "oauth"},
            "impersonate_email": {"type": "string", "title": "Impersonate Email"},
            "include_shared_drives": {"type": "boolean", "default": True},
        },
        "required": ["auth_method"],
    },
    "slack": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Slack",
        "type": "object",
        "properties": {
            "bot_token": {"type": "string", "title": "Bot Token"},
            "channels": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["bot_token"],
        "uiSchema": {"bot_token": {"ui:widget": "password"}},
    },
    "github": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "GitHub",
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "title": "Access Token"},
            "org": {"type": "string", "title": "Organization"},
            "repo": {"type": "string", "title": "Repository"},
        },
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "jira": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Jira",
        "type": "object",
        "properties": {
            "base_url": {"type": "string"},
            "email": {"type": "string"},
            "api_token": {"type": "string"},
            "project_keys": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["base_url", "email", "api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "confluence": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Confluence",
        "type": "object",
        "properties": {
            "base_url": {"type": "string"},
            "email": {"type": "string"},
            "api_token": {"type": "string"},
            "space_keys": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["base_url", "email", "api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "dropbox": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Dropbox",
        "type": "object",
        "properties": {"access_token": {"type": "string"}},
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "gmail": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Gmail",
        "type": "object",
        "properties": {
            "label": {"type": "string", "title": "Label filter", "default": "INBOX"},
        },
        "required": [],
    },
}


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
        base_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": _titleize(name),
            "type": "object",
            "properties": {},
            "required": [],
        }
        schema = RICH_SCHEMAS.get(name, base_schema)
        defs.append({"name": name, "schema": schema})
    return defs 