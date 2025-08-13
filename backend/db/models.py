from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.base import Base


# ---------------------------
# Connector credentials (MVP)
# ---------------------------
class Credential(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

    connector_name: Mapped[str] = mapped_column(String, nullable=False)
    provider_key: Mapped[str] = mapped_column(String, nullable=False)  # stable key used for locking / identity
    credential_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Enhanced credential management fields
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # OAuth token expiration
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Last refresh attempt
    refresh_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Failed refresh count
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)  # active, expired, invalid, disabled
    
    # Security and audit fields
    encryption_key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # For key rotation
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Last successful use
    created_by_ip: Mapped[str | None] = mapped_column(String, nullable=True)  # IP address of creator
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "connector_name", "provider_key", name="uq_cred_org_user_name_key"),
    )


# New audit log model for credential access
class CredentialAuditLog(Base):
    __tablename__ = "credential_audit_log"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("credential.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    
    action: Mapped[str] = mapped_column(String, nullable=False)  # created, accessed, updated, refreshed, deleted, revealed
    result: Mapped[str] = mapped_column(String, nullable=False)  # success, failure, expired, invalid
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Additional context
    
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Index for efficient querying by credential and time
        Index("ix_audit_credential_time", "credential_id", "created_at"),
        Index("ix_audit_org_time", "organization_id", "created_at"),
    )


class Organization(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    billing_plan: Mapped[str | None] = mapped_column(String, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization", cascade="all,delete-orphan")


class UserRole(str):  # simple string enum for now
    ADMIN = "admin"
    MEMBER = "member"


class User(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_pw: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.MEMBER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="users")


class UserToken(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    refresh_token_jti: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------
# Connector profiles & sync runs (Phase-1 remainder)
# --------------------------------------------------


class ConnectorProfile(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    connector_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    checkpoint_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship()
    user: Mapped["User"] = relationship()


class SyncStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class SyncRun(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connectorprofile.id"), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default=SyncStatus.PENDING, nullable=False)
    records_synced: Mapped[int | None] = mapped_column(Integer, nullable=True)

    profile: Mapped["ConnectorProfile"] = relationship()


# ---------------------------
# Destination Targets (MVP)
# ---------------------------

class DestinationTarget(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)  # destination key, e.g. "cleverbrag"
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "name", name="uq_target_org_user_name"),
    ) 