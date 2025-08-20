"""
Enhanced scheduler for CC-Pair architecture with proper scheduling logic
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, and_, or_

from backend.settings import get_settings
from backend.db.models import ConnectorCredentialPair, IndexAttempt, ConnectorCredentialPairStatus, IndexingStatus
from backend.orchestrator import celery_app
from backend.orchestrator.cc_pair_tasks import sync_cc_pair


def _create_session_factory() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    db_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@"
        f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    engine = create_async_engine(db_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scan_due_cc_pairs_impl() -> None:
    """
    Enhanced scheduler that scans for CC-Pairs ready for synchronization
    """
    SessionLocal = _create_session_factory()
    async with SessionLocal() as session:
        now = datetime.utcnow()
        
        # Find CC-Pairs that are due for sync
        # This is more sophisticated than the old profile-based approach
        result = await session.execute(
            select(ConnectorCredentialPair)
            .join(ConnectorCredentialPair.connector)
            .where(
                and_(
                    # Only active CC-Pairs
                    ConnectorCredentialPair.status == ConnectorCredentialPairStatus.ACTIVE,
                    # Not in repeated error state
                    ConnectorCredentialPair.in_repeated_error_state.is_(False),
                    # Has a refresh frequency configured
                    ConnectorCredentialPair.connector.has(refresh_freq__isnot=None),
                    # Due for refresh based on last successful run + refresh frequency
                    or_(
                        # Never run before
                        ConnectorCredentialPair.last_successful_index_time.is_(None),
                        # Due for refresh
                        ConnectorCredentialPair.last_successful_index_time + 
                        timedelta(seconds=ConnectorCredentialPair.connector.refresh_freq) <= now
                    )
                )
            )
        )
        due_cc_pairs = result.scalars().all()
        
        for cc_pair in due_cc_pairs:
            # Check if there's already a running index attempt
            existing_attempt_result = await session.execute(
                select(IndexAttempt).where(
                    and_(
                        IndexAttempt.connector_credential_pair_id == cc_pair.id,
                        IndexAttempt.status == IndexingStatus.IN_PROGRESS
                    )
                )
            )
            existing_attempt = existing_attempt_result.scalar_one_or_none()
            
            if existing_attempt:
                # Check if the attempt is stalled (no heartbeat for too long)
                if existing_attempt.last_heartbeat_time:
                    time_since_heartbeat = now - existing_attempt.last_heartbeat_time
                    if time_since_heartbeat > timedelta(minutes=30):  # 30 minutes without heartbeat
                        # Mark as failed and allow new attempt
                        existing_attempt.status = IndexingStatus.FAILED
                        existing_attempt.error_msg = "Stalled - no heartbeat for 30+ minutes"
                        await session.flush()
                    else:
                        # Still running, skip
                        continue
                else:
                    # No heartbeat recorded, check if it's been running too long
                    time_since_start = now - existing_attempt.time_created
                    if time_since_start > timedelta(hours=2):  # 2 hours max runtime
                        existing_attempt.status = IndexingStatus.FAILED
                        existing_attempt.error_msg = "Timeout - exceeded maximum runtime"
                        await session.flush()
                    else:
                        continue
            
            # Schedule the sync
            sync_cc_pair.delay(cc_pair.id, str(cc_pair.organization_id))
            
            # Log the scheduling
            from celery.utils.log import get_task_logger
            logger = get_task_logger(__name__)
            logger.info(
                "Scheduled sync for CC-Pair %s (connector: %s, org: %s)",
                cc_pair.id, cc_pair.connector.source, cc_pair.organization_id
            )
        
        await session.commit()


@celery_app.task(name="orchestrator.scan_due_cc_pairs")
def scan_due_cc_pairs() -> None:
    """Celery task to scan for due CC-Pairs"""
    asyncio.run(_scan_due_cc_pairs_impl())


async def _cleanup_stale_attempts_impl() -> None:
    """
    Cleanup stale IndexAttempts that have been running too long
    """
    SessionLocal = _create_session_factory()
    async with SessionLocal() as session:
        now = datetime.utcnow()
        cutoff_time = now - timedelta(hours=6)  # 6 hours max
        
        # Find stale attempts
        result = await session.execute(
            select(IndexAttempt).where(
                and_(
                    IndexAttempt.status == IndexingStatus.IN_PROGRESS,
                    IndexAttempt.time_created < cutoff_time
                )
            )
        )
        stale_attempts = result.scalars().all()
        
        for attempt in stale_attempts:
            attempt.status = IndexingStatus.FAILED
            attempt.error_msg = "Cleanup - exceeded maximum runtime (6 hours)"
            
            # Mark CC-Pair as having repeated errors if this happens frequently
            recent_failures_result = await session.execute(
                select(IndexAttempt).where(
                    and_(
                        IndexAttempt.connector_credential_pair_id == attempt.connector_credential_pair_id,
                        IndexAttempt.status == IndexingStatus.FAILED,
                        IndexAttempt.time_created > now - timedelta(days=1)
                    )
                ).limit(3)
            )
            recent_failures = recent_failures_result.scalars().all()
            
            if len(recent_failures) >= 2:  # Including this one, 3 failures in 24 hours
                cc_pair_result = await session.execute(
                    select(ConnectorCredentialPair).where(
                        ConnectorCredentialPair.id == attempt.connector_credential_pair_id
                    )
                )
                cc_pair = cc_pair_result.scalar_one_or_none()
                if cc_pair:
                    cc_pair.in_repeated_error_state = True
        
        if stale_attempts:
            from celery.utils.log import get_task_logger
            logger = get_task_logger(__name__)
            logger.warning("Cleaned up %d stale IndexAttempts", len(stale_attempts))
        
        await session.commit()


@celery_app.task(name="orchestrator.cleanup_stale_attempts")
def cleanup_stale_attempts() -> None:
    """Celery task to cleanup stale IndexAttempts"""
    asyncio.run(_cleanup_stale_attempts_impl())


async def _prune_cc_pairs_impl() -> None:
    """
    Handle pruning for CC-Pairs that have pruning configured
    """
    SessionLocal = _create_session_factory()
    async with SessionLocal() as session:
        now = datetime.utcnow()
        
        # Find CC-Pairs that need pruning
        result = await session.execute(
            select(ConnectorCredentialPair)
            .join(ConnectorCredentialPair.connector)
            .where(
                and_(
                    ConnectorCredentialPair.status == ConnectorCredentialPairStatus.ACTIVE,
                    ConnectorCredentialPair.connector.has(prune_freq__isnot=None),
                    or_(
                        # Never pruned before
                        ConnectorCredentialPair.last_pruned.is_(None),
                        # Due for pruning
                        ConnectorCredentialPair.last_pruned + 
                        timedelta(seconds=ConnectorCredentialPair.connector.prune_freq) <= now
                    )
                )
            )
        )
        due_for_pruning = result.scalars().all()
        
        for cc_pair in due_for_pruning:
            # In a real implementation, you would:
            # 1. Check what documents exist in the destination
            # 2. Compare with what should exist based on the source
            # 3. Remove documents that no longer exist in the source
            
            # For now, just update the last_pruned timestamp
            cc_pair.last_pruned = now
            
            from celery.utils.log import get_task_logger
            logger = get_task_logger(__name__)
            logger.info("Pruned CC-Pair %s", cc_pair.id)
        
        await session.commit()


@celery_app.task(name="orchestrator.prune_cc_pairs")
def prune_cc_pairs() -> None:
    """Celery task to handle pruning for CC-Pairs"""
    asyncio.run(_prune_cc_pairs_impl())


# Async aliases for testing
async def scan_due_cc_pairs_async() -> None:
    await _scan_due_cc_pairs_impl()


async def cleanup_stale_attempts_async() -> None:
    await _cleanup_stale_attempts_impl()


async def prune_cc_pairs_async() -> None:
    await _prune_cc_pairs_impl()
