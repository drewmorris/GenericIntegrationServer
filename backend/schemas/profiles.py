from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConnectorProfileBase(BaseModel):
    name: str = Field(..., examples=["My Google Drive"])
    source: str = Field(..., examples=["google_drive"])
    connector_config: Optional[dict[str, Any]] = Field(default_factory=dict)
    interval_minutes: int = Field(60, ge=1, le=1440)


class ConnectorProfileCreate(ConnectorProfileBase):
    organization_id: uuid.UUID
    user_id: uuid.UUID
    credential_id: uuid.UUID | None = None


class ConnectorProfileUpdate(BaseModel):
    name: Optional[str] = None
    connector_config: Optional[dict[str, Any]] = None
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    credential_id: Optional[uuid.UUID] = None


class ConnectorProfileOut(ConnectorProfileBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    next_run_at: Optional[str] | None | None
    created_at: Optional[str] | None
    credential_id: Optional[uuid.UUID] | None

    model_config = {
        "from_attributes": True,
    } 