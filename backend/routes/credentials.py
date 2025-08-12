from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db import models as m
from pydantic import BaseModel, Field
import uuid
from backend.security.crypto import encrypt_dict, maybe_decrypt_dict

router = APIRouter(prefix="/credentials", tags=["Credentials"])

class CredentialCreate(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID
    connector_name: str = Field(..., examples=["google_drive"])  # DocumentSource value
    provider_key: str = Field(..., examples=["default"])  # stable key
    credential_json: dict = Field(default_factory=dict)

class CredentialOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    connector_name: str
    provider_key: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[CredentialOut])
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    organization_id: Optional[uuid.UUID] = Query(default=None),
    user_id: Optional[uuid.UUID] = Query(default=None),
    connector_name: Optional[str] = Query(default=None),
) -> list[m.Credential]:
    stmt = select(m.Credential)
    if organization_id is not None:
        stmt = stmt.where(m.Credential.organization_id == organization_id)
    if user_id is not None:
        stmt = stmt.where(m.Credential.user_id == user_id)
    if connector_name is not None:
        stmt = stmt.where(m.Credential.connector_name == connector_name)
    res = await db.execute(stmt)
    rows = list(res.scalars().all())
    # Decrypt in-memory for response (but do not include secrets by default)
    return rows

@router.post("/", response_model=CredentialOut, status_code=status.HTTP_201_CREATED)
async def create_credential(payload: CredentialCreate, db: AsyncSession = Depends(get_db)) -> m.Credential:
    obj = m.Credential(
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        connector_name=payload.connector_name,
        provider_key=payload.provider_key,
        credential_json=encrypt_dict(payload.credential_json),
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj 