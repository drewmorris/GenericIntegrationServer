"""
Query optimization utilities for CC-Pair architecture
"""
from __future__ import annotations

from typing import Optional, Sequence
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db import models as m


async def get_cc_pairs_with_optimized_query(
    db: AsyncSession,
    organization_id: Optional[str] = None,
    status: Optional[m.ConnectorCredentialPairStatus] = None,
    connector_source: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Sequence[m.ConnectorCredentialPair]:
    """
    Optimized query for CC-Pairs with proper index usage
    
    This query is designed to leverage the following indexes:
    - idx_cc_pair_organization_id (for organization filtering)
    - idx_cc_pair_status (for status filtering) 
    - idx_connector_source (for source filtering via join)
    - idx_cc_pair_time_created (for ordering)
    """
    query = select(m.ConnectorCredentialPair).options(
        selectinload(m.ConnectorCredentialPair.connector)
    )
    
    conditions = []
    
    if organization_id:
        conditions.append(m.ConnectorCredentialPair.organization_id == organization_id)
    
    if status:
        conditions.append(m.ConnectorCredentialPair.status == status)
    
    if connector_source:
        query = query.join(m.Connector)
        conditions.append(m.Connector.source == connector_source)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by time_created (uses idx_cc_pair_time_created)
    query = query.order_by(desc(m.ConnectorCredentialPair.time_created))
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_active_index_attempts_optimized(
    db: AsyncSession,
    cc_pair_id: Optional[int] = None,
    organization_id: Optional[str] = None
) -> Sequence[m.IndexAttempt]:
    """
    Optimized query for active index attempts
    
    Uses indexes:
    - idx_index_attempt_status (for status filtering)
    - idx_index_attempt_cc_pair_id (for CC-Pair filtering)
    - idx_cc_pair_organization_id (for organization filtering via join)
    """
    query = select(m.IndexAttempt).options(
        selectinload(m.IndexAttempt.connector_credential_pair)
    )
    
    conditions = [m.IndexAttempt.status == m.IndexingStatus.IN_PROGRESS]
    
    if cc_pair_id:
        conditions.append(m.IndexAttempt.connector_credential_pair_id == cc_pair_id)
    
    if organization_id:
        query = query.join(m.ConnectorCredentialPair)
        conditions.append(m.ConnectorCredentialPair.organization_id == organization_id)
    
    query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_cc_pairs_due_for_sync_optimized(
    db: AsyncSession,
    organization_id: Optional[str] = None
) -> Sequence[m.ConnectorCredentialPair]:
    """
    Optimized query for CC-Pairs due for synchronization
    
    Uses composite index:
    - idx_cc_pair_status_org_time (status, organization_id, last_successful_index_time)
    """
    from datetime import datetime, timedelta
    
    # Calculate sync threshold (e.g., pairs not synced in last hour)
    sync_threshold = datetime.utcnow() - timedelta(hours=1)
    
    query = select(m.ConnectorCredentialPair).options(
        selectinload(m.ConnectorCredentialPair.connector)
    )
    
    conditions = [
        m.ConnectorCredentialPair.status == m.ConnectorCredentialPairStatus.ACTIVE,
        or_(
            m.ConnectorCredentialPair.last_successful_index_time.is_(None),
            m.ConnectorCredentialPair.last_successful_index_time < sync_threshold
        )
    ]
    
    if organization_id:
        conditions.append(m.ConnectorCredentialPair.organization_id == organization_id)
    
    query = query.where(and_(*conditions))
    
    # Order by last sync time (oldest first) - uses composite index
    query = query.order_by(
        m.ConnectorCredentialPair.last_successful_index_time.asc().nulls_first()
    )
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_index_attempt_statistics_optimized(
    db: AsyncSession,
    cc_pair_id: int
) -> dict:
    """
    Get optimized statistics for index attempts
    
    Uses indexes:
    - idx_index_attempt_cc_pair_id (for CC-Pair filtering)
    - idx_index_attempt_status (for status aggregation)
    """
    # Count attempts by status
    status_query = select(
        m.IndexAttempt.status,
        func.count(m.IndexAttempt.id).label('count')
    ).where(
        m.IndexAttempt.connector_credential_pair_id == cc_pair_id
    ).group_by(m.IndexAttempt.status)
    
    # Get latest attempt (uses idx_index_attempt_cc_pair_time composite index)
    latest_query = select(m.IndexAttempt).where(
        m.IndexAttempt.connector_credential_pair_id == cc_pair_id
    ).order_by(desc(m.IndexAttempt.time_created)).limit(1)
    
    # Execute both queries
    status_result = await db.execute(status_query)
    latest_result = await db.execute(latest_query)
    
    status_counts = {row.status: row.count for row in status_result}
    latest_attempt = latest_result.scalar_one_or_none()
    
    return {
        'status_counts': status_counts,
        'latest_attempt': latest_attempt,
        'total_attempts': sum(status_counts.values())
    }
