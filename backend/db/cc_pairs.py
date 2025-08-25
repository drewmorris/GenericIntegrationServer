"""
Database operations for Connector-Credential Pair architecture
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db import models as m
from backend.schemas.cc_pairs import (
    ConnectorCreate, ConnectorUpdate,
    ConnectorCredentialPairCreate, ConnectorCredentialPairUpdate,
    IndexAttemptCreate, IndexAttemptUpdate
)


# ===== CONNECTOR OPERATIONS =====

async def create_connector(
    db: AsyncSession,
    connector_data: ConnectorCreate
) -> m.Connector:
    """Create a new reusable connector configuration"""
    connector = m.Connector(
        name=connector_data.name,
        source=connector_data.source,
        input_type=connector_data.input_type,
        connector_specific_config=connector_data.connector_specific_config,
        refresh_freq=connector_data.refresh_freq,
        prune_freq=connector_data.prune_freq,
    )
    db.add(connector)
    await db.flush()
    await db.refresh(connector)
    return connector


async def get_connector(db: AsyncSession, connector_id: int) -> Optional[m.Connector]:
    """Get a connector by ID"""
    result = await db.execute(
        select(m.Connector).where(m.Connector.id == connector_id)
    )
    return result.scalar_one_or_none()


async def get_connectors(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    source: Optional[str] = None
) -> Sequence[m.Connector]:
    """Get connectors with optional filtering"""
    query = select(m.Connector)
    
    if source:
        query = query.where(m.Connector.source == source)
    
    query = query.offset(skip).limit(limit).order_by(m.Connector.time_created.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def update_connector(
    db: AsyncSession,
    connector_id: int,
    connector_data: ConnectorUpdate
) -> Optional[m.Connector]:
    """Update a connector"""
    connector = await get_connector(db, connector_id)
    if not connector:
        return None
    
    update_data = connector_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connector, field, value)
    
    connector.time_updated = datetime.utcnow()
    await db.flush()
    await db.refresh(connector)
    return connector


async def delete_connector(db: AsyncSession, connector_id: int) -> bool:
    """Delete a connector (only if no CC-Pairs exist)"""
    connector = await get_connector(db, connector_id)
    if not connector:
        return False
    
    # Check if any CC-Pairs exist
    result = await db.execute(
        select(m.ConnectorCredentialPair).where(
            m.ConnectorCredentialPair.connector_id == connector_id
        ).limit(1)
    )
    if result.scalar_one_or_none():
        raise ValueError("Cannot delete connector with existing CC-Pairs")
    
    await db.delete(connector)
    return True


# ===== CC-PAIR OPERATIONS =====

async def create_cc_pair(
    db: AsyncSession,
    cc_pair_data: ConnectorCredentialPairCreate
) -> m.ConnectorCredentialPair:
    """Create a new Connector-Credential Pair"""
    cc_pair = m.ConnectorCredentialPair(
        name=cc_pair_data.name,
        connector_id=cc_pair_data.connector_id,
        credential_id=cc_pair_data.credential_id,
        destination_target_id=cc_pair_data.destination_target_id,
        organization_id=cc_pair_data.organization_id,
        creator_id=cc_pair_data.creator_id,
        status=cc_pair_data.status,
        access_type=cc_pair_data.access_type,
        auto_sync_options=cc_pair_data.auto_sync_options,
    )
    db.add(cc_pair)
    await db.flush()
    await db.refresh(cc_pair)
    return cc_pair


async def get_cc_pair(
    db: AsyncSession, 
    cc_pair_id: int,
    include_connector: bool = False,
    include_latest_attempt: bool = False
) -> Optional[m.ConnectorCredentialPair]:
    """Get a CC-Pair by ID with optional related data"""
    query = select(m.ConnectorCredentialPair).where(m.ConnectorCredentialPair.id == cc_pair_id)
    
    if include_connector:
        query = query.options(selectinload(m.ConnectorCredentialPair.connector))
    
    if include_latest_attempt:
        query = query.options(selectinload(m.ConnectorCredentialPair.index_attempts))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_cc_pairs(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID] = None,
    creator_id: Optional[uuid.UUID] = None,
    connector_id: Optional[int] = None,
    credential_id: Optional[uuid.UUID] = None,
    status: Optional[m.ConnectorCredentialPairStatus] = None,
    skip: int = 0,
    limit: int = 100,
    include_connector: bool = False
) -> Sequence[m.ConnectorCredentialPair]:
    """Get CC-Pairs with filtering"""
    query = select(m.ConnectorCredentialPair)
    
    conditions = []
    if organization_id:
        conditions.append(m.ConnectorCredentialPair.organization_id == organization_id)
    if creator_id:
        conditions.append(m.ConnectorCredentialPair.creator_id == creator_id)
    if connector_id:
        conditions.append(m.ConnectorCredentialPair.connector_id == connector_id)
    if credential_id:
        conditions.append(m.ConnectorCredentialPair.credential_id == credential_id)
    if status:
        conditions.append(m.ConnectorCredentialPair.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    if include_connector:
        query = query.options(selectinload(m.ConnectorCredentialPair.connector))
    
    query = query.offset(skip).limit(limit).order_by(m.ConnectorCredentialPair.time_created.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def update_cc_pair(
    db: AsyncSession,
    cc_pair_id: int,
    cc_pair_data: ConnectorCredentialPairUpdate
) -> Optional[m.ConnectorCredentialPair]:
    """Update a CC-Pair"""
    cc_pair = await get_cc_pair(db, cc_pair_id)
    if not cc_pair:
        return None
    
    update_data = cc_pair_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cc_pair, field, value)
    
    cc_pair.time_updated = datetime.utcnow()
    await db.flush()
    await db.refresh(cc_pair)
    return cc_pair


async def delete_cc_pair(db: AsyncSession, cc_pair_id: int) -> bool:
    """Delete a CC-Pair"""
    cc_pair = await get_cc_pair(db, cc_pair_id)
    if not cc_pair:
        return False
    
    await db.delete(cc_pair)
    return True


# ===== INDEX ATTEMPT OPERATIONS =====

async def create_index_attempt(
    db: AsyncSession,
    attempt_data: IndexAttemptCreate
) -> m.IndexAttempt:
    """Create a new index attempt"""
    attempt = m.IndexAttempt(
        connector_credential_pair_id=attempt_data.connector_credential_pair_id,
        from_beginning=attempt_data.from_beginning,
        status=attempt_data.status,
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)
    return attempt


async def get_index_attempt(db: AsyncSession, attempt_id: int) -> Optional[m.IndexAttempt]:
    """Get an index attempt by ID"""
    result = await db.execute(
        select(m.IndexAttempt).where(m.IndexAttempt.id == attempt_id)
    )
    return result.scalar_one_or_none()


async def get_index_attempts(
    db: AsyncSession,
    cc_pair_id: Optional[int] = None,
    status: Optional[m.IndexingStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> Sequence[m.IndexAttempt]:
    """Get index attempts with filtering"""
    query = select(m.IndexAttempt)
    
    conditions = []
    if cc_pair_id:
        conditions.append(m.IndexAttempt.connector_credential_pair_id == cc_pair_id)
    if status:
        conditions.append(m.IndexAttempt.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset(skip).limit(limit).order_by(m.IndexAttempt.time_created.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_latest_index_attempt(
    db: AsyncSession,
    cc_pair_id: int
) -> Optional[m.IndexAttempt]:
    """Get the most recent index attempt for a CC-Pair"""
    result = await db.execute(
        select(m.IndexAttempt)
        .where(m.IndexAttempt.connector_credential_pair_id == cc_pair_id)
        .order_by(desc(m.IndexAttempt.time_created))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_active_index_attempts(
    db: AsyncSession,
    cc_pair_id: Optional[int] = None
) -> Sequence[m.IndexAttempt]:
    """Get currently running index attempts"""
    query = select(m.IndexAttempt).where(
        m.IndexAttempt.status == m.IndexingStatus.IN_PROGRESS
    )
    
    if cc_pair_id:
        query = query.where(m.IndexAttempt.connector_credential_pair_id == cc_pair_id)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_active_index_attempts_for_org(
    db: AsyncSession,
    organization_id: str
) -> Sequence[m.IndexAttempt]:
    """Get all active index attempts for an organization (for real-time monitoring)"""
    query = (
        select(m.IndexAttempt)
        .join(m.ConnectorCredentialPair)
        .where(
            and_(
                m.IndexAttempt.status == m.IndexingStatus.IN_PROGRESS,
                m.ConnectorCredentialPair.organization_id == uuid.UUID(organization_id)
            )
        )
        .options(selectinload(m.IndexAttempt.connector_credential_pair))
        .order_by(desc(m.IndexAttempt.time_created))
    )
    
    result = await db.execute(query)
    return result.scalars().all()


async def update_index_attempt(
    db: AsyncSession,
    attempt_id: int,
    attempt_data: IndexAttemptUpdate
) -> Optional[m.IndexAttempt]:
    """Update an index attempt"""
    attempt = await get_index_attempt(db, attempt_id)
    if not attempt:
        return None
    
    update_data = attempt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attempt, field, value)
    
    attempt.time_updated = datetime.utcnow()
    await db.flush()
    await db.refresh(attempt)
    return attempt


async def cancel_index_attempt(db: AsyncSession, attempt_id: int) -> bool:
    """Cancel a running index attempt"""
    attempt = await get_index_attempt(db, attempt_id)
    if not attempt:
        return False
    
    if attempt.status != m.IndexingStatus.IN_PROGRESS:
        return False
    
    attempt.cancellation_requested = True
    attempt.status = m.IndexingStatus.CANCELED
    attempt.time_updated = datetime.utcnow()
    await db.flush()
    return True


# ===== UTILITY FUNCTIONS =====

async def get_cc_pair_with_details(
    db: AsyncSession,
    cc_pair_id: int,
    organization_id: Optional[uuid.UUID] = None
) -> Optional[m.ConnectorCredentialPair]:
    """Get CC-Pair with full details including connector and latest attempt"""
    query = (
        select(m.ConnectorCredentialPair)
        .options(
            selectinload(m.ConnectorCredentialPair.connector),
            selectinload(m.ConnectorCredentialPair.index_attempts)
        )
        .where(m.ConnectorCredentialPair.id == cc_pair_id)
    )
    
    if organization_id:
        query = query.where(m.ConnectorCredentialPair.organization_id == organization_id)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_cc_pairs_for_sync(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID] = None
) -> Sequence[m.ConnectorCredentialPair]:
    """Get CC-Pairs that are ready for synchronization"""
    query = (
        select(m.ConnectorCredentialPair)
        .options(selectinload(m.ConnectorCredentialPair.connector))
        .where(m.ConnectorCredentialPair.status == m.ConnectorCredentialPairStatus.ACTIVE)
    )
    
    if organization_id:
        query = query.where(m.ConnectorCredentialPair.organization_id == organization_id)
    
    result = await db.execute(query)
    return result.scalars().all()
