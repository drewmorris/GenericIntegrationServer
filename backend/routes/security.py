from __future__ import annotations

from typing import List, Optional, Dict, Tuple
from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
import uuid
import os
from datetime import datetime, timedelta

from backend.db.session import get_db
from backend.db.models import Credential, CredentialAuditLog
from backend.security.crypto import validate_encryption_setup, generate_new_key, needs_key_rotation
import logging

router = APIRouter(prefix="/security", tags=["Security"])
logger = logging.getLogger(__name__)


class EncryptionStatus(BaseModel):
	valid: bool
	key_count: int
	current_version: int
	rotation_days: int
	max_versions: int
	has_dev_fallback: bool
	credentials_needing_rotation: int
	error: Optional[str] = None


class AuditLogEntry(BaseModel):
	id: uuid.UUID
	credential_id: uuid.UUID
	action: str
	result: str
	details: dict
	ip_address: Optional[str] = None
	user_agent: Optional[str] = None
	created_at: datetime

	model_config = {"from_attributes": True}


class KeyRotationRequest(BaseModel):
	confirm: bool = False


class KeyRotationResponse(BaseModel):
	new_key: str
	version: int
	instructions: str


@router.get(
	"/encryption/status", 
	response_model=EncryptionStatus,
	summary="Get encryption status",
	description="Retrieve the current status of the encryption system including key version, "
				"credentials needing rotation, and overall encryption health. Requires admin access."
)
async def get_encryption_status(
	db: AsyncSession = Depends(get_db),
	x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret", description="Admin secret for privileged operations")
) -> EncryptionStatus:
	"""Get the current encryption system status."""
	admin_key = os.getenv("ADMIN_API_KEY")
	if not admin_key or x_admin_secret != admin_key:
		raise HTTPException(status_code=403, detail="Admin access required")
	
	# Get encryption validation results
	status = validate_encryption_setup()
	
	# Count credentials needing rotation
	res = await db.execute(select(Credential))
	credentials = res.scalars().all()
	
	needing_rotation = sum(1 for cred in credentials if needs_key_rotation(cred.credential_json))
	
	return EncryptionStatus(
		valid=status["valid"],
		key_count=status["key_count"],
		current_version=status["current_version"],
		rotation_days=status.get("rotation_days", 90),
		max_versions=status.get("max_versions", 3),
		has_dev_fallback=status.get("has_dev_fallback", False),
		credentials_needing_rotation=needing_rotation,
		error=status.get("error")
	)


@router.post("/encryption/rotate-key", response_model=KeyRotationResponse)
async def rotate_encryption_key(
	request: KeyRotationRequest,
	x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")
) -> KeyRotationResponse:
	"""Generate a new encryption key for rotation."""
	admin_key = os.getenv("ADMIN_API_KEY")
	if not admin_key or x_admin_secret != admin_key:
		raise HTTPException(status_code=403, detail="Admin access required")
	
	if not request.confirm:
		raise HTTPException(
			status_code=400, 
			detail="Key rotation must be confirmed. Set 'confirm: true' in request body."
		)
	
	# Generate new key
	new_key = generate_new_key()
	
	# Determine next version
	current_version = 1
	for v in range(2, 10):  # Check up to version 10
		if os.getenv(f"CREDENTIALS_SECRET_KEY_V{v}"):
			current_version = v
		else:
			break
	
	next_version = current_version + 1
	
	instructions = f"""
Key rotation instructions:

1. Set the new key as environment variable:
   CREDENTIALS_SECRET_KEY_V{next_version}={new_key}

2. Restart the application to load the new key

3. Use the /security/credentials/rotate-all endpoint to re-encrypt all credentials

4. After successful rotation, you can remove older key versions (keep at least 2 versions)

Note: The new key will be used for all new encryptions. Existing credentials will be 
automatically rotated when accessed or can be bulk rotated using the rotate-all endpoint.
"""
	
	logger.info("Generated new encryption key version %d", next_version)
	
	return KeyRotationResponse(
		new_key=new_key,
		version=next_version,
		instructions=instructions.strip()
	)


@router.post("/credentials/rotate-all")
async def rotate_all_credentials(
	db: AsyncSession = Depends(get_db),
	x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")
) -> dict:
	"""Rotate encryption for all credentials that need it."""
	admin_key = os.getenv("ADMIN_API_KEY")
	if not admin_key or x_admin_secret != admin_key:
		raise HTTPException(status_code=403, detail="Admin access required")
	
	try:
		from backend.security.crypto import rotate_encryption
		
		# Get all credentials
		res = await db.execute(select(Credential))
		credentials = res.scalars().all()
		
		rotated_count = 0
		error_count = 0
		
		for cred in credentials:
			try:
				if needs_key_rotation(cred.credential_json):
					rotated_data = rotate_encryption(cred.credential_json)
					cred.credential_json = rotated_data
					cred.encryption_key_version = rotated_data.get("_enc_version", 1)
					cred.updated_at = datetime.utcnow()
					rotated_count += 1
			except Exception as e:
				logger.error("Failed to rotate credential %s: %s", cred.id, str(e))
				error_count += 1
		
		if rotated_count > 0:
			await db.commit()
		
		logger.info("Bulk credential rotation completed: %d rotated, %d errors", rotated_count, error_count)
		
		return {
			"rotated_count": rotated_count,
			"error_count": error_count,
			"total_credentials": len(credentials)
		}
		
	except Exception as e:
		logger.error("Bulk credential rotation failed: %s", str(e))
		await db.rollback()
		raise HTTPException(status_code=500, detail="Bulk rotation failed")


@router.get(
	"/audit/credentials", 
	response_model=List[AuditLogEntry],
	summary="Get credential audit logs",
	description="Retrieve audit logs for credential operations with optional filtering. "
				"Shows who accessed, modified, or tested credentials with timestamps and IP addresses. "
				"Essential for security compliance and troubleshooting."
)
async def get_credential_audit_logs(
	db: AsyncSession = Depends(get_db),
	credential_id: Optional[uuid.UUID] = Query(default=None, description="Filter by specific credential ID"),
	organization_id: Optional[uuid.UUID] = Query(default=None, description="Filter by organization"),
	action: Optional[str] = Query(default=None, description="Filter by action type (access, modify, test, etc.)"),
	result: Optional[str] = Query(default=None),
	limit: int = Query(default=100, le=1000),
	offset: int = Query(default=0, ge=0),
	x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")
) -> List[CredentialAuditLog]:
	"""Get credential audit logs (admin only)."""
	admin_key = os.getenv("ADMIN_API_KEY")
	if not admin_key or x_admin_secret != admin_key:
		raise HTTPException(status_code=403, detail="Admin access required")
	
	stmt = select(CredentialAuditLog).order_by(desc(CredentialAuditLog.created_at))
	
	if credential_id:
		stmt = stmt.where(CredentialAuditLog.credential_id == credential_id)
	if organization_id:
		stmt = stmt.where(CredentialAuditLog.organization_id == organization_id)
	if action:
		stmt = stmt.where(CredentialAuditLog.action == action)
	if result:
		stmt = stmt.where(CredentialAuditLog.result == result)
	
	stmt = stmt.offset(offset).limit(limit)
	
	res = await db.execute(stmt)
	logs = res.scalars().all()
	
	logger.info("audit_logs_query count=%d filters=%s", len(logs), {
		"credential_id": credential_id,
		"organization_id": organization_id,
		"action": action,
		"result": result
	})
	
	return list(logs)


@router.get("/audit/credentials/stats")
async def get_credential_audit_stats(
	db: AsyncSession = Depends(get_db),
	days: int = Query(default=30, ge=1, le=365),
	x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")
) -> dict:
	"""Get credential audit statistics."""
	admin_key = os.getenv("ADMIN_API_KEY")
	if not admin_key or x_admin_secret != admin_key:
		raise HTTPException(status_code=403, detail="Admin access required")
	
	since = datetime.utcnow() - timedelta(days=days)
	
	# Get action counts
	action_result = await db.execute(
		select(CredentialAuditLog.action, func.count(CredentialAuditLog.id))
		.where(CredentialAuditLog.created_at >= since)
		.group_by(CredentialAuditLog.action)
	)
	action_rows: List[Tuple[str, int]] = [(row[0], row[1]) for row in action_result.fetchall()]
	action_counts: Dict[str, int] = {k: int(v) for k, v in action_rows}
	
	# Get result counts
	result_result = await db.execute(
		select(CredentialAuditLog.result, func.count(CredentialAuditLog.id))
		.where(CredentialAuditLog.created_at >= since)
		.group_by(CredentialAuditLog.result)
	)
	result_rows: List[Tuple[str, int]] = [(row[0], row[1]) for row in result_result.fetchall()]
	result_counts: Dict[str, int] = {k: int(v) for k, v in result_rows}
	
	# Get total count
	total_result = await db.execute(
		select(func.count(CredentialAuditLog.id))
		.where(CredentialAuditLog.created_at >= since)
	)
	total_count = int(total_result.scalar() or 0)
	
	# Get unique credentials accessed
	unique_creds_result = await db.execute(
		select(func.count(func.distinct(CredentialAuditLog.credential_id)))
		.where(CredentialAuditLog.created_at >= since)
	)
	unique_credentials = int(unique_creds_result.scalar() or 0)
	
	return {
		"period_days": days,
		"total_events": total_count,
		"unique_credentials": unique_credentials,
		"action_counts": action_counts,
		"result_counts": result_counts,
		"since": since.isoformat()
	} 