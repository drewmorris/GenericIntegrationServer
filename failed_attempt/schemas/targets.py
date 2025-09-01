from __future__ import annotations

import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field

class DestinationTargetBase(BaseModel):
    name: str = Field(..., examples=["cleverbrag"])  # registry key
    display_name: str = Field(..., examples=["CleverBrag Prod"])  # user label
    config: dict[str, Any] = Field(default_factory=dict)

class DestinationTargetCreate(DestinationTargetBase):
    # organization_id and user_id are extracted from JWT token, not from request body
    pass

class DestinationTargetUpdate(BaseModel):
    display_name: Optional[str] = None
    config: Optional[dict[str, Any]] = None

class DestinationTargetOut(DestinationTargetBase):
    id: uuid.UUID

    model_config = {"from_attributes": True} 