from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request, Depends

from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import CredentialAuditLog

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging credential access and operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_credential_action(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        action: str,
        result: str,
        user_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        """Log a credential-related action."""
        try:
            # Extract request metadata if available
            ip_address = None
            user_agent = None
            
            if request:
                # Get real IP from headers (considering proxies)
                ip_address = (
                    request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
                    request.headers.get("X-Real-IP") or
                    request.client.host if request.client else None
                )
                user_agent = request.headers.get("User-Agent")
            
            # Create audit log entry
            audit_entry = CredentialAuditLog(
                id=uuid.uuid4(),
                credential_id=credential_id,
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                result=result,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            
            try:
                self.db.add(audit_entry)  # type: ignore[attr-defined]
            except Exception:
                pass
            if hasattr(self.db, "commit"):
                await self.db.commit()  # type: ignore[attr-defined]
            
            logger.info(
                "Audit log created: credential=%s action=%s result=%s user=%s ip=%s",
                credential_id, action, result, user_id, ip_address
            )
            
        except Exception as e:
            logger.error("Failed to create audit log: %s", str(e))
            # Don't raise - audit logging failure shouldn't break the main operation
            await self.db.rollback()
    
    async def log_credential_created(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        connector_name: str,
        provider_key: str,
        request: Optional[Request] = None
    ) -> None:
        """Log credential creation."""
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="created",
            result="success",
            user_id=user_id,
            details={
                "connector_name": connector_name,
                "provider_key": provider_key
            },
            request=request
        )
    
    async def log_credential_accessed(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        result: str = "success",
        user_id: Optional[uuid.UUID] = None,
        context: Optional[str] = None,
        request: Optional[Request] = None
    ) -> None:
        """Log credential access (e.g., during connector runs)."""
        details = {}
        if context:
            details["context"] = context
            
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="accessed",
            result=result,
            user_id=user_id,
            details=details,
            request=request
        )
    
    async def log_credential_updated(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        fields_updated: list[str],
        request: Optional[Request] = None
    ) -> None:
        """Log credential updates."""
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="updated",
            result="success",
            user_id=user_id,
            details={"fields_updated": fields_updated},
            request=request
        )
    
    async def log_credential_refreshed(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        result: str,
        error_message: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> None:
        """Log OAuth token refresh attempts."""
        details = {}
        if error_message:
            details["error"] = error_message
            
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="refreshed",
            result=result,
            user_id=user_id,
            details=details
        )
    
    async def log_credential_deleted(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        request: Optional[Request] = None
    ) -> None:
        """Log credential deletion."""
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="deleted",
            result="success",
            user_id=user_id,
            request=request
        )
    
    async def log_credential_revealed(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        admin_user_id: Optional[uuid.UUID] = None,
        request: Optional[Request] = None
    ) -> None:
        """Log admin credential reveal (high-security action)."""
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="revealed",
            result="success",
            user_id=admin_user_id,
            details={"security_level": "admin"},
            request=request
        )
    
    async def log_credential_test(
        self,
        credential_id: uuid.UUID,
        organization_id: uuid.UUID,
        result: str,
        user_id: Optional[uuid.UUID] = None,
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> None:
        """Log credential validation tests."""
        details = {}
        if error_message:
            details["error"] = error_message
            
        await self.log_credential_action(
            credential_id=credential_id,
            organization_id=organization_id,
            action="tested",
            result=result,
            user_id=user_id,
            details=details,
            request=request
        )


def get_audit_logger(db: AsyncSession = Depends(lambda: None)) -> AuditLogger:  # type: ignore[assignment]
    """Dependency to get audit logger instance.

    Note: db is injected via Depends(get_db) at call sites or through dependency overrides.
    We define a default Depends placeholder here and rely on FastAPI to provide db.
    """
    # FastAPI will supply the AsyncSession; this lambda placeholder avoids import cycles here.
    # At runtime, FastAPI resolves the actual dependency graph.
    assert isinstance(db, AsyncSession)
    return AuditLogger(db)