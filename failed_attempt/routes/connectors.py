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
            "auth_method": {"type": "string", "enum": ["oauth", "service_account"], "default": "oauth", "description": "Authentication method used to access Google Drive"},
            "impersonate_email": {"type": "string", "title": "Impersonate Email", "description": "For service accounts, the user to impersonate"},
            "include_shared_drives": {"type": "boolean", "default": True, "description": "Include files from shared drives"},
        },
        "required": ["auth_method"],
    },
    "slack": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Slack",
        "type": "object",
        "properties": {
            "bot_token": {"type": "string", "title": "Bot Token", "description": "xoxb- token with required scopes"},
            "channels": {"type": "array", "items": {"type": "string"}, "description": "Optional channel IDs to limit scope"},
        },
        "required": ["bot_token"],
        "uiSchema": {"bot_token": {"ui:widget": "password"}},
    },
    "github": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "GitHub",
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "title": "Access Token", "description": "PAT with repo scope"},
            "org": {"type": "string", "title": "Organization", "description": "Optional GitHub organization"},
            "repo": {"type": "string", "title": "Repository", "description": "Optional single repository (owner/name)"},
        },
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "jira": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Jira",
        "type": "object",
        "properties": {
            "base_url": {"type": "string", "description": "e.g. https://your-domain.atlassian.net"},
            "email": {"type": "string", "description": "User email for API token"},
            "api_token": {"type": "string", "description": "Jira API token"},
            "project_keys": {"type": "array", "items": {"type": "string"}, "description": "Limit to specific projects (optional)"},
        },
        "required": ["base_url", "email", "api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "confluence": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Confluence",
        "type": "object",
        "properties": {
            "base_url": {"type": "string", "description": "e.g. https://your-domain.atlassian.net/wiki"},
            "email": {"type": "string"},
            "api_token": {"type": "string"},
            "space_keys": {"type": "array", "items": {"type": "string"}, "description": "Limit to spaces (optional)"},
        },
        "required": ["base_url", "email", "api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "dropbox": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Dropbox",
        "type": "object",
        "properties": {"access_token": {"type": "string", "description": "Access token"}},
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "gmail": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Gmail",
        "type": "object",
        "properties": {
            "label": {"type": "string", "title": "Label filter", "default": "INBOX", "description": "Only fetch messages with this label"},
        },
        "required": [],
    },
    "gitlab": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "GitLab",
        "type": "object",
        "properties": {
            "access_token": {"type": "string", "description": "PAT with api scope"},
            "project": {"type": "string", "description": "project path e.g. group/name (optional)"},
            "host": {"type": "string", "description": "Self-hosted base URL (optional)", "default": "https://gitlab.com"},
        },
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "notion": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Notion",
        "type": "object",
        "properties": {"integration_token": {"type": "string", "title": "Integration Token"}},
        "required": ["integration_token"],
        "uiSchema": {"integration_token": {"ui:widget": "password"}},
    },
    "linear": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Linear",
        "type": "object",
        "properties": {"api_key": {"type": "string", "title": "API Key"}},
        "required": ["api_key"],
        "uiSchema": {"api_key": {"ui:widget": "password"}},
    },
    "hubspot": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "HubSpot",
        "type": "object",
        "properties": {"access_token": {"type": "string", "title": "Access Token"}},
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "zendesk": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Zendesk",
        "type": "object",
        "properties": {
            "subdomain": {"type": "string", "description": "yourcompany.zendesk.com subdomain"},
            "email": {"type": "string"},
            "api_token": {"type": "string"},
        },
        "required": ["subdomain", "email", "api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "sharepoint": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "SharePoint",
        "type": "object",
        "properties": {
            "tenant_id": {"type": "string"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
            "site_url": {"type": "string"},
        },
        "required": ["tenant_id", "client_id", "client_secret", "site_url"],
        "uiSchema": {"client_secret": {"ui:widget": "password"}},
    },
    "google_sites": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Google Sites",
        "type": "object",
        "properties": {"site": {"type": "string", "description": "Site name or URL"}},
        "required": ["site"],
    },
    "airtable": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Airtable",
        "type": "object",
        "properties": {
            "api_key": {"type": "string"},
            "base_id": {"type": "string"},
            "table": {"type": "string"},
        },
        "required": ["api_key", "base_id", "table"],
        "uiSchema": {"api_key": {"ui:widget": "password"}},
    },
    "asana": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Asana",
        "type": "object",
        "properties": {
            "access_token": {"type": "string"},
            "workspace": {"type": "string"},
            "project": {"type": "string"},
        },
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "salesforce": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Salesforce",
        "type": "object",
        "properties": {
            "instance_url": {"type": "string", "description": "https://your-instance.my.salesforce.com"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "security_token": {"type": "string"},
        },
        "required": ["instance_url", "client_id", "client_secret", "username", "password", "security_token"],
        "uiSchema": {"client_secret": {"ui:widget": "password"}, "password": {"ui:widget": "password"}},
    },
    "teams": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Microsoft Teams",
        "type": "object",
        "properties": {
            "tenant_id": {"type": "string"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
        },
        "required": ["tenant_id", "client_id", "client_secret"],
        "uiSchema": {"client_secret": {"ui:widget": "password"}},
    },
    "imap": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "IMAP",
        "type": "object",
        "properties": {
            "host": {"type": "string", "default": "imap.gmail.com"},
            "port": {"type": "integer", "default": 993},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "use_ssl": {"type": "boolean", "default": True},
        },
        "required": ["host", "port", "username", "password"],
        "uiSchema": {"password": {"ui:widget": "password"}},
    },
    "mediawiki": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MediaWiki",
        "type": "object",
        "properties": {"api_url": {"type": "string", "description": "https://wiki.example.org/api.php"}},
        "required": ["api_url"],
    },
    "wikipedia": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Wikipedia",
        "type": "object",
        "properties": {"language": {"type": "string", "default": "en"}},
        "required": [],
    },
    "web": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Web Crawler",
        "type": "object",
        "properties": {
            "start_urls": {"type": "array", "items": {"type": "string"}},
            "max_depth": {"type": "integer", "default": 2, "description": "Maximum crawl depth"},
        },
        "required": ["start_urls"],
    },
    "file": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Local Files",
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory or file path"}},
        "required": ["path"],
    },
    "clickup": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ClickUp",
        "type": "object",
        "properties": {"api_token": {"type": "string"}},
        "required": ["api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "productboard": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Productboard",
        "type": "object",
        "properties": {"api_token": {"type": "string"}},
        "required": ["api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "discourse": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Discourse",
        "type": "object",
        "properties": {
            "base_url": {"type": "string"},
            "api_key": {"type": "string"},
            "api_username": {"type": "string"},
        },
        "required": ["base_url", "api_key", "api_username"],
        "uiSchema": {"api_key": {"ui:widget": "password"}},
    },
    "egnyte": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Egnyte",
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "yourdomain.egnyte.com"},
            "access_token": {"type": "string"},
        },
        "required": ["domain", "access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "guru": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Guru",
        "type": "object",
        "properties": {"api_token": {"type": "string"}},
        "required": ["api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "loopio": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Loopio",
        "type": "object",
        "properties": {"api_token": {"type": "string"}},
        "required": ["api_token"],
        "uiSchema": {"api_token": {"ui:widget": "password"}},
    },
    "highspot": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Highspot",
        "type": "object",
        "properties": {"access_token": {"type": "string"}},
        "required": ["access_token"],
        "uiSchema": {"access_token": {"ui:widget": "password"}},
    },
    "google_cloud_storage": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Google Cloud Storage",
        "type": "object",
        "properties": {"bucket": {"type": "string"}},
        "required": ["bucket"],
    },
    "oci_storage": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "OCI Object Storage",
        "type": "object",
        "properties": {"bucket": {"type": "string"}},
        "required": ["bucket"],
    },
    "s3": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Amazon S3",
        "type": "object",
        "properties": {"bucket": {"type": "string"}},
        "required": ["bucket"],
    },
    "r2": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Cloudflare R2",
        "type": "object",
        "properties": {"bucket": {"type": "string"}},
        "required": ["bucket"],
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