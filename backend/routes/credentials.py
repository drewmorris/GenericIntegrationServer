from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db import models as m
from pydantic import BaseModel, Field
import uuid
from backend.security.crypto import encrypt_dict, maybe_decrypt_dict, needs_key_rotation, rotate_encryption
from backend.security.redact import mask_secrets
from backend.security.audit import get_audit_logger, AuditLogger
import logging
import os
from datetime import datetime

router = APIRouter(prefix="/credentials", tags=["Credentials"])
logger = logging.getLogger(__name__)

class CredentialCreate(BaseModel):
	organization_id: uuid.UUID
	user_id: uuid.UUID
	connector_name: str = Field(..., examples=["google_drive"])  # DocumentSource value
	provider_key: str = Field(..., examples=["default"])  # stable key
	credential_json: dict = Field(default_factory=dict)
	expires_at: Optional[datetime] = None  # For OAuth tokens

class CredentialOut(BaseModel):
	id: uuid.UUID
	organization_id: uuid.UUID
	user_id: uuid.UUID
	connector_name: str
	provider_key: str
	status: str
	expires_at: Optional[datetime] = None
	last_used_at: Optional[datetime] = None
	last_refreshed_at: Optional[datetime] = None
	refresh_attempts: int
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True

@router.get("/", response_model=List[CredentialOut])
async def list_credentials(
	db: AsyncSession = Depends(get_db),
	organization_id: Optional[uuid.UUID] = Query(default=None),
	user_id: Optional[uuid.UUID] = Query(default=None),
	connector_name: Optional[str] = Query(default=None),
	status: Optional[str] = Query(default=None),
) -> list[m.Credential]:
	stmt = select(m.Credential)
	if organization_id is not None:
		stmt = stmt.where(m.Credential.organization_id == organization_id)
	if user_id is not None:
		stmt = stmt.where(m.Credential.user_id == user_id)
	if connector_name is not None:
		stmt = stmt.where(m.Credential.connector_name == connector_name)
	if status is not None:
		stmt = stmt.where(m.Credential.status == status)
	
	res = await db.execute(stmt)
	rows = list(res.scalars().all())
	logger.info("credentials_list count=%s filters=%s", len(rows), {
		"organization_id": organization_id,
		"user_id": user_id, 
		"connector_name": connector_name,
		"status": status
	})
	return rows

@router.post("/", response_model=CredentialOut, status_code=status.HTTP_201_CREATED)
async def create_credential(
	request: Request,
	payload: CredentialCreate,
	db: AsyncSession = Depends(get_db),
	audit_logger: AuditLogger = Depends(get_audit_logger),  # type: ignore[assignment]
) -> m.Credential:
	try:
		# Get client IP for audit logging
		client_ip = (
			request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
			request.headers.get("X-Real-IP") or
			request.client.host if request.client else None
		)
		
		obj = m.Credential(
			id=uuid.uuid4(),
			organization_id=payload.organization_id,
			user_id=payload.user_id,
			connector_name=payload.connector_name,
			provider_key=payload.provider_key,
			credential_json=encrypt_dict(payload.credential_json),
			expires_at=payload.expires_at,
			status="active",
			encryption_key_version=1,
			created_by_ip=client_ip,
			created_at=datetime.utcnow(),
			updated_at=datetime.utcnow()
		)
		db.add(obj)
		await db.commit()
		await db.refresh(obj)
		
		# Audit log the creation
		await audit_logger.log_credential_created(
			credential_id=obj.id,
			organization_id=obj.organization_id,
			user_id=obj.user_id,
			connector_name=obj.connector_name,
			provider_key=obj.provider_key,
			request=request
		)
		
		logger.info("credential_create id=%s connector=%s user=%s", obj.id, obj.connector_name, obj.user_id)
		return obj
		
	except Exception as e:
		logger.error("Failed to create credential: %s", str(e))
		await db.rollback()
		raise HTTPException(status_code=500, detail="Failed to create credential")

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
		"status": row.status,
		"expires_at": row.expires_at.isoformat() if row.expires_at else None,
		"last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
		"last_refreshed_at": row.last_refreshed_at.isoformat() if row.last_refreshed_at else None,
		"refresh_attempts": row.refresh_attempts,
		"created_at": row.created_at.isoformat(),
		"updated_at": row.updated_at.isoformat(),
		"needs_rotation": needs_key_rotation(row.credential_json)
	}

class CredentialUpdate(BaseModel):
	provider_key: Optional[str] = None
	credential_json: Optional[dict] = None
	expires_at: Optional[datetime] = None
	status: Optional[str] = None

@router.patch("/{cred_id}", response_model=CredentialOut)
async def update_credential(
	request: Request,
	cred_id: uuid.UUID, 
	payload: CredentialUpdate, 
	db: AsyncSession = Depends(get_db),
	audit_logger: AuditLogger = Depends(get_audit_logger),  # type: ignore[assignment]
) -> m.Credential:
	row = await db.get(m.Credential, cred_id)
	if row is None:
		raise HTTPException(status_code=404, detail="Credential not found")
	
	fields_updated = []
	
	if payload.provider_key is not None:
		row.provider_key = payload.provider_key
		fields_updated.append("provider_key")
	
	if payload.credential_json is not None:
		# Check if we need to rotate encryption
		if needs_key_rotation(row.credential_json):
			logger.info("Rotating encryption during credential update for %s", cred_id)
		
		row.credential_json = encrypt_dict(payload.credential_json)
		row.encryption_key_version = 1  # New encryption uses current key
		fields_updated.append("credential_json")
	
	if payload.expires_at is not None:
		row.expires_at = payload.expires_at
		fields_updated.append("expires_at")
	
	if payload.status is not None:
		row.status = payload.status
		fields_updated.append("status")
	
	row.updated_at = datetime.utcnow()
	
	await db.commit()
	await db.refresh(row)
	
	# Audit log the update
	await audit_logger.log_credential_updated(
		credential_id=row.id,
		organization_id=row.organization_id,
		user_id=row.user_id,
		fields_updated=fields_updated,
		request=request
	)
	
	logger.info("credential_update id=%s fields=%s", cred_id, fields_updated)
	return row

@router.delete("/{cred_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
	request: Request,
	cred_id: uuid.UUID, 
	db: AsyncSession = Depends(get_db),
	audit_logger: AuditLogger = Depends(get_audit_logger),  # type: ignore[assignment]
) -> None:
	row = await db.get(m.Credential, cred_id)
	if row is None:
		return
	
	# Audit log before deletion
	await audit_logger.log_credential_deleted(
		credential_id=row.id,
		organization_id=row.organization_id,
		user_id=row.user_id,
		request=request
	)
	
	await db.delete(row)
	await db.commit()
	logger.info("credential_delete id=%s", cred_id)

class CredentialTestResult(BaseModel):
	ok: bool
	detail: Optional[str] = None
	needs_refresh: bool = False

@router.post("/{cred_id}/test", response_model=CredentialTestResult)
async def test_credential(
	request: Request,
	cred_id: uuid.UUID, 
	db: AsyncSession = Depends(get_db),
	audit_logger: AuditLogger = Depends(get_audit_logger),  # type: ignore[assignment]
) -> CredentialTestResult:
	row = await db.get(m.Credential, cred_id)
	if row is None:
		raise HTTPException(status_code=404, detail="Credential not found")
	
	try:
		from connectors.onyx.configs.constants import DocumentSource  # type: ignore
		from connectors.onyx.connectors.factory import identify_connector_class  # type: ignore
		
		src = getattr(DocumentSource, row.connector_name.upper())
		conn_cls = identify_connector_class(src)
		conn = conn_cls()
		
		if hasattr(conn, 'load_credentials'):
			# Decrypt and load credentials
			creds = maybe_decrypt_dict(row.credential_json)
			conn.load_credentials(creds)
		
		# Basic validation if exposed
		if hasattr(conn, 'validate_connector_settings'):
			conn.validate_connector_settings()
		
		# Update last_used_at
		row.last_used_at = datetime.utcnow()
		await db.commit()
		
		# Audit log successful test
		await audit_logger.log_credential_test(
			credential_id=row.id,
			organization_id=row.organization_id,
			result="success",
			request=request
		)
		
		logger.info("credential_test id=%s ok=true", cred_id)
		return CredentialTestResult(ok=True, needs_refresh=row.status == "expired")
		
	except Exception as exc:
		error_msg = str(exc)
		
		# Check if this is an authentication/authorization error
		is_auth_error = any(keyword in error_msg.lower() for keyword in [
			"unauthorized", "forbidden", "invalid", "expired", "authentication", "token"
		])
		
		if is_auth_error and row.status != "expired":
			# Mark credential as expired if it's an auth error
			row.status = "expired"
			row.updated_at = datetime.utcnow()
			await db.commit()
		
		# Audit log failed test
		await audit_logger.log_credential_test(
			credential_id=row.id,
			organization_id=row.organization_id,
			result="failure",
			error_message=error_msg,
			request=request
		)
		
		logger.info("credential_test id=%s ok=false error=%s", cred_id, error_msg)
		return CredentialTestResult(
			ok=False, 
			detail=error_msg,
			needs_refresh=is_auth_error
		)

@router.post("/{cred_id}/rotate", response_model=CredentialOut)
async def rotate_credential_encryption(
	request: Request,
	cred_id: uuid.UUID,
	db: AsyncSession = Depends(get_db),
	audit_logger: AuditLogger = Depends(get_audit_logger),  # type: ignore[assignment]
) -> m.Credential:
	"""Manually rotate the encryption of a credential."""
	row = await db.get(m.Credential, cred_id)
	if row is None:
		raise HTTPException(status_code=404, detail="Credential not found")
	
	if not needs_key_rotation(row.credential_json):
		raise HTTPException(status_code=400, detail="Credential encryption does not need rotation")
	
	try:
		# Rotate the encryption
		rotated_data = rotate_encryption(row.credential_json)
		row.credential_json = rotated_data
		row.encryption_key_version = rotated_data.get("_enc_version", 1)
		row.updated_at = datetime.utcnow()
		
		await db.commit()
		await db.refresh(row)
		
		# Audit log the rotation
		await audit_logger.log_credential_updated(
			credential_id=row.id,
			organization_id=row.organization_id,
			user_id=row.user_id,
			fields_updated=["encryption_rotation"],
			request=request
		)
		
		logger.info("credential_rotate id=%s new_version=%s", cred_id, row.encryption_key_version)
		return row
		
	except Exception as e:
		logger.error("Failed to rotate credential encryption: %s", str(e))
		await db.rollback()
		raise HTTPException(status_code=500, detail="Failed to rotate encryption")

@router.get("/{cred_id}/reveal")
async def reveal_credential(
	request: Request,
	cred_id: uuid.UUID,
	db: AsyncSession = Depends(get_db),
	audit_logger: AuditLogger = Depends(get_audit_logger),  # type: ignore[assignment]
	x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
) -> dict:
	admin_key = os.getenv("ADMIN_API_KEY")
	if not admin_key or x_admin_secret != admin_key:
		raise HTTPException(status_code=403, detail="Forbidden")
	
	row = await db.get(m.Credential, cred_id)
	if row is None:
		raise HTTPException(status_code=404, detail="Credential not found")
	
	# Audit log the reveal (high-security action)
	await audit_logger.log_credential_revealed(
		credential_id=row.id,
		organization_id=row.organization_id,
		request=request
	)
	
	logger.info("credential_reveal id=%s", cred_id)
	return {
		"id": str(row.id),
		"organization_id": str(row.organization_id),
		"user_id": str(row.user_id),
		"connector_name": row.connector_name,
		"provider_key": row.provider_key,
		"credential_json": maybe_decrypt_dict(row.credential_json),
		"status": row.status,
		"expires_at": row.expires_at.isoformat() if row.expires_at else None,
		"encryption_key_version": row.encryption_key_version,
		"created_at": row.created_at.isoformat(),
		"updated_at": row.updated_at.isoformat()
	} 