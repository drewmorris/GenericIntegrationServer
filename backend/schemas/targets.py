from __future__ import annotations

import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field

class DestinationTargetBase(BaseModel):
    name: str = Field(..., examples=["cleverbrag"])  # registry key
    display_name: str = Field(..., examples=["CleverBrag Prod"])  # user label
    config: dict[str, Any] = Field(default_factory=dict)

class DestinationTargetCreate(DestinationTargetBase):
    organization_id: uuid.UUID
    user_id: uuid.UUID

class DestinationTargetOut(DestinationTargetBase):
    id: uuid.UUID

    model_config = {"from_attributes": True} 