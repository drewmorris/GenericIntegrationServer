from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, UniqueConstraint, Index, Enum, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column, declared_attr
from enum import Enum as PyEnum

from backend.db.base import Base
from backend.auth.schemas import UserRole


# ---------------------------
# Enums for Connector/Sync Status
# ---------------------------

class ConnectorCredentialPairStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETING = "DELETING"


class IndexingStatus(str, PyEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class AccessType(str, PyEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    SYNC = "SYNC"


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
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "credential_audit_log"
    
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


class User(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_pw: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.BASIC.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="users")


class UserToken(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    refresh_token_jti: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------
# Connector models (CC-Pair Architecture)
# --------------------------------------------------

class Connector(Base):
    """Reusable connector configuration that can be linked to multiple credentials"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)  # DocumentSource value
    input_type: Mapped[str] = mapped_column(String, nullable=False)  # InputType value
    connector_specific_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Scheduling configuration
    refresh_freq: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    prune_freq: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    
    # Timestamps
    time_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    connector_credential_pairs: Mapped[list["ConnectorCredentialPair"]] = relationship(
        "ConnectorCredentialPair", back_populates="connector", cascade="all, delete-orphan"
    )


class ConnectorCredentialPair(Base):
    """Links connectors to credentials with sync status and configuration"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Foreign keys
    connector_id: Mapped[int] = mapped_column(ForeignKey("connector.id"), nullable=False)
    credential_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("credential.id"), nullable=False)
    destination_target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("destinationtarget.id"), nullable=True
    )
    
    # Multi-tenant fields
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    creator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    
    # Status and configuration
    status: Mapped[ConnectorCredentialPairStatus] = mapped_column(
        Enum(ConnectorCredentialPairStatus, native_enum=False), default=ConnectorCredentialPairStatus.ACTIVE
    )
    access_type: Mapped[AccessType] = mapped_column(
        Enum(AccessType, native_enum=False), default=AccessType.PRIVATE
    )
    
    # Advanced sync options
    auto_sync_options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_time_perm_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_successful_index_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_pruned: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_docs_indexed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Error tracking
    in_repeated_error_state: Mapped[bool] = mapped_column(Boolean, default=False)
    deletion_failure_message: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Timestamps
    time_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    connector: Mapped["Connector"] = relationship("Connector", back_populates="connector_credential_pairs")
    credential: Mapped["Credential"] = relationship("Credential")
    destination_target: Mapped["DestinationTarget"] = relationship("DestinationTarget")
    organization: Mapped["Organization"] = relationship("Organization")
    creator: Mapped["User"] = relationship("User")
    index_attempts: Mapped[list["IndexAttempt"]] = relationship("IndexAttempt", back_populates="connector_credential_pair")


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
    credential_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("credential.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

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


class IndexAttempt(Base):
    """Enhanced sync tracking with progress monitoring and batch coordination"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Link to CC-Pair
    connector_credential_pair_id: Mapped[int] = mapped_column(
        ForeignKey("connectorcredentialpair.id"), nullable=False
    )
    
    # Status and progress
    status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus, native_enum=False), default=IndexingStatus.NOT_STARTED
    )
    from_beginning: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Document counts
    new_docs_indexed: Mapped[int] = mapped_column(Integer, default=0)
    total_docs_indexed: Mapped[int] = mapped_column(Integer, default=0)
    docs_removed_from_index: Mapped[int] = mapped_column(Integer, default=0)
    
    # Error tracking
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_exception_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Batch coordination
    total_batches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_batches: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    
    # Progress tracking for stall detection
    last_progress_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_batches_completed_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Heartbeat tracking for worker liveness
    heartbeat_counter: Mapped[int] = mapped_column(Integer, default=0)
    last_heartbeat_value: Mapped[int] = mapped_column(Integer, default=0)
    last_heartbeat_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Celery task coordination
    celery_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Checkpoint tracking
    checkpoint_pointer: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Timestamps
    time_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_started: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    time_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    connector_credential_pair: Mapped["ConnectorCredentialPair"] = relationship(
        "ConnectorCredentialPair", back_populates="index_attempts"
    )


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


# ---------------------------
# API Key Management 
# ---------------------------
class ApiKey(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    hashed_api_key: Mapped[str] = mapped_column(String, unique=True)
    api_key_display: Mapped[str] = mapped_column(String, unique=True)
    # the ID of the "user" who represents the access credentials for the API key
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    # the ID of the user who owns the key
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Add this relationship to access the User object via user_id
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id]) 