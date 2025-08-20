"""
Pydantic schemas for Connector-Credential Pair architecture
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models import ConnectorCredentialPairStatus, IndexingStatus, AccessType


# ===== CONNECTOR SCHEMAS =====

class ConnectorBase(BaseModel):
    name: str = Field(..., description="Human-readable connector name")
    source: str = Field(..., description="DocumentSource value (e.g., 'slack', 'google_drive')")
    input_type: str = Field(..., description="InputType value (e.g., 'LOAD_STATE', 'POLL')")
    connector_specific_config: Dict[str, Any] = Field(default_factory=dict, description="Connector configuration")
    refresh_freq: Optional[int] = Field(None, description="Refresh frequency in seconds")
    prune_freq: Optional[int] = Field(None, description="Prune frequency in seconds")


class ConnectorCreate(ConnectorBase):
    pass


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    connector_specific_config: Optional[Dict[str, Any]] = None
    refresh_freq: Optional[int] = None
    prune_freq: Optional[int] = None


class ConnectorOut(ConnectorBase):
    id: int
    time_created: datetime
    time_updated: datetime

    model_config = ConfigDict(from_attributes=True)


# ===== CC-PAIR SCHEMAS =====

class ConnectorCredentialPairBase(BaseModel):
    name: str = Field(..., description="Human-readable CC-Pair name")
    connector_id: int = Field(..., description="ID of the connector")
    credential_id: uuid.UUID = Field(..., description="ID of the credential")
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    creator_id: Optional[uuid.UUID] = Field(None, description="User who created this CC-Pair")
    status: ConnectorCredentialPairStatus = Field(default=ConnectorCredentialPairStatus.ACTIVE)
    access_type: AccessType = Field(default=AccessType.PRIVATE)
    auto_sync_options: Optional[Dict[str, Any]] = Field(None, description="Permission sync configuration")


class ConnectorCredentialPairCreate(ConnectorCredentialPairBase):
    pass


class ConnectorCredentialPairUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ConnectorCredentialPairStatus] = None
    access_type: Optional[AccessType] = None
    auto_sync_options: Optional[Dict[str, Any]] = None


class ConnectorCredentialPairOut(ConnectorCredentialPairBase):
    id: int
    last_time_perm_sync: Optional[datetime] = None
    last_successful_index_time: Optional[datetime] = None
    last_pruned: Optional[datetime] = None
    total_docs_indexed: int = 0
    in_repeated_error_state: bool = False
    deletion_failure_message: Optional[str] = None
    time_created: datetime
    time_updated: datetime

    # Related objects
    connector: Optional[ConnectorOut] = None
    
    model_config = ConfigDict(from_attributes=True)


# ===== INDEX ATTEMPT SCHEMAS =====

class IndexAttemptBase(BaseModel):
    connector_credential_pair_id: int = Field(..., description="CC-Pair ID")
    from_beginning: bool = Field(default=False, description="Whether this is a full re-index")
    status: IndexingStatus = Field(default=IndexingStatus.NOT_STARTED)


class IndexAttemptCreate(IndexAttemptBase):
    pass


class IndexAttemptUpdate(BaseModel):
    status: Optional[IndexingStatus] = None
    new_docs_indexed: Optional[int] = None
    total_docs_indexed: Optional[int] = None
    docs_removed_from_index: Optional[int] = None
    error_msg: Optional[str] = None
    full_exception_trace: Optional[str] = None
    total_batches: Optional[int] = None
    completed_batches: Optional[int] = None
    total_chunks: Optional[int] = None
    last_progress_time: Optional[datetime] = None
    last_batches_completed_count: Optional[int] = None
    heartbeat_counter: Optional[int] = None
    last_heartbeat_value: Optional[int] = None
    last_heartbeat_time: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    cancellation_requested: Optional[bool] = None
    checkpoint_pointer: Optional[str] = None
    time_started: Optional[datetime] = None


class IndexAttemptOut(IndexAttemptBase):
    id: int
    new_docs_indexed: int = 0
    total_docs_indexed: int = 0
    docs_removed_from_index: int = 0
    error_msg: Optional[str] = None
    full_exception_trace: Optional[str] = None
    total_batches: Optional[int] = None
    completed_batches: int = 0
    total_chunks: int = 0
    last_progress_time: Optional[datetime] = None
    last_batches_completed_count: int = 0
    heartbeat_counter: int = 0
    last_heartbeat_value: int = 0
    last_heartbeat_time: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    cancellation_requested: bool = False
    checkpoint_pointer: Optional[str] = None
    time_created: datetime
    time_started: Optional[datetime] = None
    time_updated: datetime

    # Related objects
    connector_credential_pair: Optional[ConnectorCredentialPairOut] = None

    model_config = ConfigDict(from_attributes=True)


# ===== COMBINED SCHEMAS FOR CONVENIENCE =====

class ConnectorCredentialPairWithDetails(ConnectorCredentialPairOut):
    """CC-Pair with full connector and latest index attempt details"""
    connector: ConnectorOut
    latest_index_attempt: Optional[IndexAttemptOut] = None
    active_index_attempts: list[IndexAttemptOut] = Field(default_factory=list)


class ConnectorWithCCPairs(ConnectorOut):
    """Connector with all its CC-Pairs"""
    connector_credential_pairs: list[ConnectorCredentialPairOut] = Field(default_factory=list)
