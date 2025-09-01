"""
Metrics collection service that aggregates data and triggers alerts
Integrates with Prometheus metrics and alerting system
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal
from backend.db import models as m
from backend.monitoring.alerting import alert_manager, AlertType
from backend.monitoring.destination_metrics import DestinationStatus

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and aggregates metrics for alerting and monitoring
    Follows Onyx's background task patterns
    """
    
    def __init__(self):
        self._running = False
        self._collection_interval = 300  # 5 minutes
        self._metrics_cache: Dict[str, Any] = {}
        self._error_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    async def start_collection(self) -> None:
        """Start the metrics collection background task"""
        if self._running:
            logger.warning("Metrics collection is already running")
            return
        
        self._running = True
        logger.info("Starting metrics collection service")
        
        while self._running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self._collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_collection(self) -> None:
        """Stop the metrics collection"""
        self._running = False
        logger.info("Stopping metrics collection service")
    
    async def _collect_metrics(self) -> None:
        """Collect metrics from database and trigger alerts"""
        logger.debug("Collecting metrics for alerting")
        
        async with AsyncSessionLocal() as session:
            # Collect destination health metrics
            await self._collect_destination_metrics(session)
            
            # Collect CC-Pair sync metrics
            await self._collect_cc_pair_metrics(session)
            
            # Collect organization-level metrics
            await self._collect_organization_metrics(session)
    
    async def _collect_destination_metrics(self, session: AsyncSession) -> None:
        """Collect destination-specific metrics"""
        try:
            # Get all destination targets with recent activity
            result = await session.execute(
                select(m.DestinationTarget)
                .join(m.ConnectorCredentialPair, m.ConnectorCredentialPair.destination_target_id == m.DestinationTarget.id)
                .where(m.ConnectorCredentialPair.status == m.ConnectorCredentialPairStatus.ACTIVE)
                .distinct()
            )
            
            destinations = result.scalars().all()
            
            for dest in destinations:
                await self._evaluate_destination_health(session, dest)
                
        except Exception as e:
            logger.error(f"Error collecting destination metrics: {e}")
    
    async def _evaluate_destination_health(
        self, 
        session: AsyncSession, 
        destination: m.DestinationTarget
    ) -> None:
        """Evaluate health metrics for a specific destination"""
        try:
            # Get recent index attempts for this destination
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            result = await session.execute(
                select(m.IndexAttempt)
                .join(m.ConnectorCredentialPair)
                .where(
                    m.ConnectorCredentialPair.destination_target_id == destination.id,
                    m.IndexAttempt.time_created >= one_hour_ago
                )
                .order_by(m.IndexAttempt.time_created.desc())
                .limit(50)
            )
            
            recent_attempts = result.scalars().all()
            
            if not recent_attempts:
                return
            
            # Calculate error rate
            total_attempts = len(recent_attempts)
            failed_attempts = len([a for a in recent_attempts if a.status == m.IndexingStatus.FAILED])
            error_rate = (failed_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            
            # Calculate average response time (using time_updated - time_started for completed attempts)
            completed_attempts = [
                a for a in recent_attempts 
                if a.status == m.IndexingStatus.SUCCESS and a.time_started
            ]
            
            avg_response_time = 0.0
            if completed_attempts:
                durations = [
                    (a.time_updated - a.time_started).total_seconds()
                    for a in completed_attempts
                    if a.time_started and a.time_updated
                ]
                avg_response_time = sum(durations) / len(durations) if durations else 0.0
            
            # Determine health status
            health_status = 1.0  # Healthy
            if error_rate > 50:
                health_status = 0.0  # Down
            elif error_rate > 20 or avg_response_time > 300:  # 5 minutes
                health_status = 0.5  # Degraded
            
            # Prepare metrics for alert evaluation
            metrics = {
                'destination_health_status': health_status,
                'error_rate_percent': error_rate,
                'total_requests': total_attempts,
                'error_count': failed_attempts,
                'avg_response_time': avg_response_time,
                'last_error': recent_attempts[0].error_msg if failed_attempts > 0 else None
            }
            
            # Trigger alert evaluation
            alert_manager.evaluate_metrics(
                organization_id=str(destination.organization_id),
                destination_name=destination.name,
                target_id=str(destination.id),
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Error evaluating destination health for {destination.name}: {e}")
    
    async def _collect_cc_pair_metrics(self, session: AsyncSession) -> None:
        """Collect CC-Pair sync metrics"""
        try:
            # Get active CC-Pairs
            result = await session.execute(
                select(m.ConnectorCredentialPair)
                .where(m.ConnectorCredentialPair.status == m.ConnectorCredentialPairStatus.ACTIVE)
                .options(
                    # Load related data
                    # Note: In a real implementation, you'd use proper eager loading
                )
            )
            
            cc_pairs = result.scalars().all()
            
            for cc_pair in cc_pairs:
                await self._evaluate_cc_pair_health(session, cc_pair)
                
        except Exception as e:
            logger.error(f"Error collecting CC-Pair metrics: {e}")
    
    async def _evaluate_cc_pair_health(
        self, 
        session: AsyncSession, 
        cc_pair: m.ConnectorCredentialPair
    ) -> None:
        """Evaluate health metrics for a specific CC-Pair"""
        try:
            # Get recent sync attempts
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            
            result = await session.execute(
                select(m.IndexAttempt)
                .where(
                    m.IndexAttempt.connector_credential_pair_id == cc_pair.id,
                    m.IndexAttempt.time_created >= one_day_ago
                )
                .order_by(m.IndexAttempt.time_created.desc())
                .limit(20)
            )
            
            recent_attempts = result.scalars().all()
            
            if not recent_attempts:
                return
            
            # Calculate failure metrics
            failed_attempts = [a for a in recent_attempts if a.status == m.IndexingStatus.FAILED]
            sync_failure_count = len(failed_attempts)
            
            # Find last successful sync
            successful_attempts = [a for a in recent_attempts if a.status == m.IndexingStatus.SUCCESS]
            last_successful_sync_hours = 0.0
            
            if successful_attempts:
                last_success = successful_attempts[0].time_updated
                last_successful_sync_hours = (datetime.utcnow() - last_success).total_seconds() / 3600
            else:
                last_successful_sync_hours = 48.0  # Assume 48 hours if no recent success
            
            # Calculate average sync duration
            completed_syncs = [
                a for a in recent_attempts 
                if a.status == m.IndexingStatus.SUCCESS and a.time_started and a.time_updated
            ]
            
            avg_sync_duration_minutes = 0.0
            if completed_syncs:
                durations = [
                    (a.time_updated - a.time_started).total_seconds() / 60
                    for a in completed_syncs
                    if a.time_started is not None
                ]
                avg_sync_duration_minutes = sum(durations) / len(durations) if durations else 0.0
            
            # Get destination info
            destination_name = "unknown"
            if cc_pair.destination_target_id:
                dest_result = await session.execute(
                    select(m.DestinationTarget).where(
                        m.DestinationTarget.id == cc_pair.destination_target_id
                    )
                )
                dest_target = dest_result.scalar_one_or_none()
                if dest_target:
                    destination_name = dest_target.name
            
            # Prepare metrics for alert evaluation
            metrics = {
                'sync_failure_count': sync_failure_count,
                'last_successful_sync_hours': last_successful_sync_hours,
                'avg_sync_duration_minutes': avg_sync_duration_minutes,
                'failure_count': sync_failure_count,
                'connector_source': cc_pair.connector.source if cc_pair.connector else "unknown",
                'last_success_time': successful_attempts[0].time_updated.isoformat() if successful_attempts else "never"
            }
            
            # Trigger alert evaluation
            alert_manager.evaluate_metrics(
                organization_id=str(cc_pair.organization_id),
                destination_name=destination_name,
                cc_pair_id=str(cc_pair.id),
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Error evaluating CC-Pair health for {cc_pair.id}: {e}")
    
    async def _collect_organization_metrics(self, session: AsyncSession) -> None:
        """Collect organization-level metrics"""
        try:
            # Get organization stats
            result = await session.execute(
                select(
                    m.ConnectorCredentialPair.organization_id,
                    func.count(m.ConnectorCredentialPair.id).label('cc_pair_count'),
                    func.count(
                        func.distinct(m.ConnectorCredentialPair.destination_target_id)
                    ).label('destination_count')
                )
                .where(m.ConnectorCredentialPair.status == m.ConnectorCredentialPairStatus.ACTIVE)
                .group_by(m.ConnectorCredentialPair.organization_id)
            )
            
            org_stats = result.all()
            
            for org_id, cc_pair_count, destination_count in org_stats:
                # Store organization metrics (could be used for capacity planning alerts)
                self._metrics_cache[f"org_{org_id}_cc_pairs"] = cc_pair_count
                self._metrics_cache[f"org_{org_id}_destinations"] = destination_count
                
        except Exception as e:
            logger.error(f"Error collecting organization metrics: {e}")
    
    def get_cached_metrics(self, key: str) -> Any:
        """Get cached metrics value"""
        return self._metrics_cache.get(key)
    
    def record_error(self, destination_name: str, error_type: str) -> None:
        """Record an error for rate calculation"""
        key = f"{destination_name}_{error_type}"
        self._error_counts[key].append(datetime.utcnow())
    
    def record_response_time(self, destination_name: str, duration: float) -> None:
        """Record response time for performance monitoring"""
        key = f"{destination_name}_response_time"
        self._response_times[key].append((datetime.utcnow(), duration))
    
    def get_error_rate(self, destination_name: str, minutes: int = 60) -> float:
        """Calculate error rate for the specified time window"""
        key = f"{destination_name}_error"
        if key not in self._error_counts:
            return 0.0
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_errors = [
            error_time for error_time in self._error_counts[key]
            if error_time >= cutoff_time
        ]
        
        return len(recent_errors)  # Return count, rate calculation depends on total requests


# Global metrics collector instance
metrics_collector = MetricsCollector()
