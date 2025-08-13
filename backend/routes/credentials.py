from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db import models as m
from pydantic import BaseModel, Field
import uuid
from backend.security.crypto import encrypt_dict, maybe_decrypt_dict
from backend.security.redact import mask_secrets
import logging
import os

router = APIRouter(prefix="/credentials", tags=["Credentials"])
logger = logging.getLogger(__name__)

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
    logger.info("credentials_list count=%s", len(rows))
    return rows

@router.get("/{cred_id}")
async def get_credential(cred_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(m.Credential, cred_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    logger.info("credential_get id=%s connector=%s", cred_id, row.connector_name)
    # Redact secret by default; return metadata and id only
    return {
        "id": str(row.id),
        "organization_id": str(row.organization_id),
        "user_id": str(row.user_id),
        "connector_name": row.connector_name,
        "provider_key": row.provider_key,
    }

class CredentialUpdate(BaseModel):
    provider_key: Optional[str] = None
    credential_json: Optional[dict] = None

@router.patch("/{cred_id}", response_model=CredentialOut)
async def update_credential(cred_id: uuid.UUID, payload: CredentialUpdate, db: AsyncSession = Depends(get_db)) -> m.Credential:
    row = await db.get(m.Credential, cred_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    if payload.provider_key is not None:
        row.provider_key = payload.provider_key
    if payload.credential_json is not None:
        row.credential_json = encrypt_dict(payload.credential_json)
    await db.commit()
    await db.refresh(row)
    logger.info("credential_update id=%s fields=%s", cred_id, list(payload.model_dump(exclude_none=True).keys()))
    return row

@router.delete("/{cred_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(cred_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    row = await db.get(m.Credential, cred_id)
    if row is None:
        return
    await db.delete(row)
    await db.commit()
    logger.info("credential_delete id=%s", cred_id)
    return

class CredentialTestResult(BaseModel):
    ok: bool
    detail: Optional[str] = None

@router.post("/{cred_id}/test", response_model=CredentialTestResult)
async def test_credential(cred_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CredentialTestResult:
    row = await db.get(m.Credential, cred_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    try:
        from connectors.onyx.configs.constants import DocumentSource  # type: ignore
        from connectors.onyx.connectors.factory import identify_connector_class  # type: ignore
        from connectors.onyx.connectors.interfaces import CredentialsConnector  # type: ignore
        src = getattr(DocumentSource, row.connector_name.upper())
        conn_cls = identify_connector_class(src)
        conn = conn_cls()
        if hasattr(conn, 'load_credentials'):
            # decrypt and load
            creds = row.credential_json
            conn.load_credentials(creds)
        # basic validation if exposed
        if hasattr(conn, 'validate_connector_settings'):
            conn.validate_connector_settings()
        logger.info("credential_test id=%s ok=true", cred_id)
        return CredentialTestResult(ok=True)
    except Exception as exc:  # noqa: BLE001
        logger.info("credential_test id=%s ok=false error=%s", cred_id, str(exc))
        return CredentialTestResult(ok=False, detail=str(exc))


@router.get("/{cred_id}/reveal")
async def reveal_credential(
    cred_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
) -> dict:
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key or x_admin_secret != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    row = await db.get(m.Credential, cred_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    logger.info("credential_reveal id=%s", cred_id)
    return {
        "id": str(row.id),
        "organization_id": str(row.organization_id),
        "user_id": str(row.user_id),
        "connector_name": row.connector_name,
        "provider_key": row.provider_key,
        "credential_json": maybe_decrypt_dict(row.credential_json),
    } 