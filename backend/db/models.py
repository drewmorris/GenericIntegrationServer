from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Organization(Base):
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: str = Column(String, unique=True, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    billing_plan: str | None = Column(String, nullable=True)
    settings: dict | None = Column(JSONB, nullable=True)

    users = relationship("User", back_populates="organization", cascade="all,delete-orphan")


class UserRole(str):  # simple string enum for now
    ADMIN = "admin"
    MEMBER = "member"


class User(Base):
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)

    email: str = Column(String, unique=True, nullable=False, index=True)
    hashed_pw: str = Column(String, nullable=False)
    role: str = Column(String, default=UserRole.MEMBER, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="users")


class UserToken(Base):
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    refresh_token_jti: str = Column(String, nullable=False, unique=True)
    expires_at: datetime = Column(DateTime, nullable=False)

    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------
# Connector profiles & sync runs (Phase-1 remainder)
# --------------------------------------------------


class ConnectorProfile(Base):
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)

    name: str = Column(String, nullable=False)
    source: str = Column(String, nullable=False)  # eg. "google_drive"
    connector_config: dict | None = Column(JSONB, nullable=True)
    schedule_cron: str | None = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization")


class SyncStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class SyncRun(Base):
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("connectorprofile.id"), nullable=False)

    started_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: datetime | None = Column(DateTime, nullable=True)
    status: str = Column(String, default=SyncStatus.PENDING, nullable=False)
    records_synced: int | None = Column(Integer, nullable=True)

    profile = relationship("ConnectorProfile") 