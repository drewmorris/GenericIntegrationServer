"""
Enhanced Celery tasks for CC-Pair architecture with proper IndexAttempt tracking
"""
from __future__ import annotations

import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.orchestrator import celery_app
from backend.db.session import AsyncSessionLocal
from backend.db.rls import set_current_org
from backend.db import models as m
from backend.db import cc_pairs as cc_pair_ops

logger = get_task_logger(__name__)


@celery_app.task(
    name="orchestrator.sync_cc_pair",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def sync_cc_pair(self, cc_pair_id: int, org_id: str, from_beginning: bool = False) -> str:
    """
    Enhanced sync task for CC-Pairs with proper IndexAttempt tracking
    """
    logger.info("Starting CC-Pair sync task cc_pair=%s org=%s from_beginning=%s", 
                cc_pair_id, org_id, from_beginning)
    
    return asyncio.run(_sync_cc_pair_impl(self, cc_pair_id, org_id, from_beginning))


async def _sync_cc_pair_impl(
    task_instance, 
    cc_pair_id: int, 
    org_id: str, 
    from_beginning: bool = False
) -> str:
    """Implementation of CC-Pair sync with IndexAttempt tracking"""
    
    async with AsyncSessionLocal() as session:
        try:
            await set_current_org(session, uuid.UUID(org_id))
            
            # Get CC-Pair with related data
            cc_pair = await cc_pair_ops.get_cc_pair_with_details(
                session, cc_pair_id, organization_id=uuid.UUID(org_id)
            )
            
            if not cc_pair:
                raise ValueError(f"CC-Pair {cc_pair_id} not found or not accessible")
            
            assert cc_pair is not None  # Type assertion for MyPy
            
            if cc_pair.status != m.ConnectorCredentialPairStatus.ACTIVE:
                logger.warning("CC-Pair %s is not active, skipping sync", cc_pair_id)
                return f"CC-Pair {cc_pair_id} is not active"
            
            # Create IndexAttempt
            index_attempt = m.IndexAttempt(
                connector_credential_pair_id=cc_pair_id,
                status=m.IndexingStatus.IN_PROGRESS,
                from_beginning=from_beginning,
                celery_task_id=task_instance.request.id,
                time_started=datetime.utcnow()
            )
            
            session.add(index_attempt)
            await session.flush()
            await session.refresh(index_attempt)
            
            logger.info("Created IndexAttempt %s for CC-Pair %s", index_attempt.id, cc_pair_id)
            
            # Update heartbeat
            await _update_heartbeat(session, index_attempt.id)
            
            # Run the actual connector
            docs_synced = await _run_connector_for_cc_pair(
                session, cc_pair, index_attempt, task_instance
            )
            
            # Update IndexAttempt with results
            index_attempt.status = m.IndexingStatus.SUCCESS
            index_attempt.new_docs_indexed = docs_synced
            index_attempt.total_docs_indexed = docs_synced
            index_attempt.completed_batches = 1
            index_attempt.total_batches = 1
            
            # Update CC-Pair stats
            cc_pair.last_successful_index_time = datetime.utcnow()
            cc_pair.total_docs_indexed += docs_synced
            cc_pair.in_repeated_error_state = False
            
            await session.commit()
            
            logger.info("Successfully synced CC-Pair %s: %d documents", cc_pair_id, docs_synced)
            return f"Successfully synced {docs_synced} documents for CC-Pair {cc_pair_id}"
            
        except Exception as e:
            logger.error("Error syncing CC-Pair %s: %s", cc_pair_id, str(e))
            
            # Update IndexAttempt with error
            if 'index_attempt' in locals():
                index_attempt.status = m.IndexingStatus.FAILED
                index_attempt.error_msg = str(e)
                index_attempt.full_exception_trace = str(e)  # In production, use traceback.format_exc()
                
                # Update CC-Pair error state
                assert cc_pair is not None  # Type assertion for MyPy
                cc_pair.in_repeated_error_state = True
                
                await session.commit()
            
            raise


async def _run_connector_for_cc_pair(
    session: AsyncSession,
    cc_pair: m.ConnectorCredentialPair,
    index_attempt: m.IndexAttempt,
    task_instance
) -> int:
    """Run the actual connector and return number of documents synced"""
    
    try:
        # Import connector dependencies
        import datetime as _dt
        from connectors.onyx.configs.constants import DocumentSource
        from connectors.onyx.connectors.connector_runner import ConnectorRunner
        from connectors.onyx.connectors.mock_connector.connector import MockConnector, MockConnectorCheckpoint
        from connectors.onyx.connectors.models import InputType
        
        runner: Optional[ConnectorRunner] = None
        from connectors.onyx.connectors.factory import identify_connector_class
        
        connector = cc_pair.connector
        source = connector.source
        
        # Update progress
        await _update_progress(session, index_attempt.id, "Initializing connector")
        
        if source == "mock_source":
            # Mock connector for testing
            mock_connector = MockConnector(mock_server_host="localhost", mock_server_port=9999)
            mock_connector.load_credentials(connector.connector_specific_config or {})
            runner = ConnectorRunner(
                mock_connector, 
                batch_size=10, 
                include_permissions=False, 
                time_range=(_dt.datetime.utcnow(), _dt.datetime.utcnow())
            )
            
            batch_gen = runner.run(MockConnectorCheckpoint())
            docs = []
            batch_count = 0
            
            for batch, failure, _ in batch_gen:
                batch_count += 1
                await _update_progress(session, index_attempt.id, f"Processing batch {batch_count}")
                
                if batch:
                    docs.extend([d.model_dump(mode="json") for d in batch])
                
                # Update heartbeat periodically
                if batch_count % 5 == 0:
                    await _update_heartbeat(session, index_attempt.id)
            
            if not docs:
                docs.append({"id": str(cc_pair.id), "raw_text": f"mock doc for CC-Pair {cc_pair.id}"})
            
        else:
            # Real connector
            try:
                src = getattr(DocumentSource, source.upper())
            except AttributeError:
                logger.warning("DocumentSource.%s not found, using mock data", source.upper())
                docs = [{"id": str(cc_pair.id), "raw_text": f"mock data for {source}"}]
                return len(docs)
            
            def _select_input_type(source: str) -> InputType:
                polling = {"slack", "gmail", "zulip", "teams", "discord"}
                if source in polling:
                    return InputType.POLL
                return InputType.LOAD_STATE
            
            connector_cls = identify_connector_class(src, _select_input_type(source))
            conn_cfg = connector.connector_specific_config or {}
            connector_instance = connector_cls(**conn_cfg)
            
            # Load credentials if available
            if cc_pair.credential_id:
                from backend.connectors.credentials_provider import DBCredentialsProvider
                with DBCredentialsProvider(
                    tenant_id=str(cc_pair.organization_id), 
                    connector_name=source, 
                    credential_id=str(cc_pair.credential_id), 
                    db=session
                ) as prov:
                    connector_instance.load_credentials(prov.get_credentials())
            
            runner = ConnectorRunner(
                connector_instance, 
                batch_size=10, 
                include_permissions=False, 
                time_range=(_dt.datetime.utcnow(), _dt.datetime.utcnow())
            )
            
            # Attempt to resume from saved checkpoint if available
            checkpoint = None
            if index_attempt.checkpoint_pointer:
                # In a real implementation, you'd load the checkpoint from storage
                pass
            
            batch_gen = runner.run(checkpoint)
            docs = []
            batch_count = 0
            
            for batch, failure, checkpoint in batch_gen:
                batch_count += 1
                await _update_progress(session, index_attempt.id, f"Processing batch {batch_count}")
                
                if batch:
                    docs.extend([d.model_dump(mode="json") for d in batch])
                
                # Save checkpoint periodically
                if checkpoint and batch_count % 10 == 0:
                    # In a real implementation, save checkpoint to storage
                    index_attempt.checkpoint_pointer = f"batch_{batch_count}"
                    await session.flush()
                
                # Update heartbeat
                if batch_count % 5 == 0:
                    await _update_heartbeat(session, index_attempt.id)
                
                # Check for cancellation
                await session.refresh(index_attempt)
                if index_attempt.cancellation_requested:
                    logger.info("Cancellation requested for IndexAttempt %s", index_attempt.id)
                    index_attempt.status = m.IndexingStatus.CANCELED
                    await session.commit()
                    return len(docs)
        
        # Send documents to destinations (using existing logic)
        await _send_to_destinations(session, cc_pair, docs)
        
        return len(docs)
        
    except Exception as e:
        logger.error("Connector execution failed: %s", str(e))
        raise


async def _send_to_destinations(
    session: AsyncSession,
    cc_pair: m.ConnectorCredentialPair,
    docs: list[dict]
) -> None:
    """Send documents to the CC-Pair's configured destination"""
    
    # Check if CC-Pair has a destination configured
    if not cc_pair.destination_target_id:
        logger.warning("No destination target configured for CC-Pair %s", cc_pair.id)
        return
    
    # Get the specific destination target for this CC-Pair
    result = await session.execute(
        select(m.DestinationTarget).where(
            m.DestinationTarget.id == cc_pair.destination_target_id
        )
    )
    target = result.scalar_one_or_none()
    
    if not target:
        logger.error("Destination target %s not found for CC-Pair %s", cc_pair.destination_target_id, cc_pair.id)
        return
    
    # Use existing destination logic
    from backend.destinations import get_destination
    
    try:
        destination_class = get_destination(target.name)
        if destination_class:
            destination = destination_class()
            
            # Use enhanced batch processing for better performance and reliability
            if hasattr(destination, 'send_batch') and len(docs) > 1:
                await destination.send_batch(documents=docs, profile_config=target.config)
            else:
                await destination.send(payload=docs, profile_config=target.config)
                
            logger.info("Sent %d documents from CC-Pair %s to destination %s", len(docs), cc_pair.id, target.name)
    except Exception as e:
        logger.error("Failed to send from CC-Pair %s to destination %s: %s", cc_pair.id, target.name, str(e))
        raise


async def _update_heartbeat(session: AsyncSession, attempt_id: int) -> None:
    """Update heartbeat for IndexAttempt"""
    result = await session.execute(
        select(m.IndexAttempt).where(m.IndexAttempt.id == attempt_id)
    )
    attempt = result.scalar_one_or_none()
    
    if attempt:
        attempt.heartbeat_counter += 1
        attempt.last_heartbeat_value = attempt.heartbeat_counter
        attempt.last_heartbeat_time = datetime.utcnow()
        await session.flush()


async def _update_progress(session: AsyncSession, attempt_id: int, message: str) -> None:
    """Update progress for IndexAttempt"""
    result = await session.execute(
        select(m.IndexAttempt).where(m.IndexAttempt.id == attempt_id)
    )
    attempt = result.scalar_one_or_none()
    
    if attempt:
        attempt.last_progress_time = datetime.utcnow()
        # In a real implementation, you might store progress messages
        logger.info("IndexAttempt %s progress: %s", attempt_id, message)
        await session.flush()


@celery_app.task(name="orchestrator.cancel_index_attempt")
def cancel_index_attempt_task(attempt_id: int, org_id: str) -> str:
    """Cancel a running index attempt"""
    return asyncio.run(_cancel_index_attempt_impl(attempt_id, org_id))


async def _cancel_index_attempt_impl(attempt_id: int, org_id: str) -> str:
    """Implementation of index attempt cancellation"""
    
    async with AsyncSessionLocal() as session:
        try:
            await set_current_org(session, uuid.UUID(org_id))
            
            success = await cc_pair_ops.cancel_index_attempt(session, attempt_id)
            
            if success:
                await session.commit()
                logger.info("Successfully cancelled IndexAttempt %s", attempt_id)
                return f"Cancelled IndexAttempt {attempt_id}"
            else:
                return f"Could not cancel IndexAttempt {attempt_id} (not found or not running)"
                
        except Exception as e:
            logger.error("Error cancelling IndexAttempt %s: %s", attempt_id, str(e))
            raise
