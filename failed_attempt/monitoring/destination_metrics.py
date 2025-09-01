"""
Destination-specific Prometheus metrics for CC-Pair architecture
Extends Onyx's monitoring patterns with destination-aware metrics
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)


class DestinationStatus(str, Enum):
    """Destination health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    DOWN = "down"
    UNKNOWN = "unknown"


class CCPairStatus(str, Enum):
    """CC-Pair sync status"""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SYNCING = "syncing"


# =============================================================================
# Destination Performance Metrics (adapted from Onyx patterns)
# =============================================================================

# Document delivery metrics
destination_documents_sent_total = Counter(
    'destination_documents_sent_total',
    'Total number of documents sent to destinations',
    ['destination_name', 'organization_id', 'cc_pair_id', 'status']
)

destination_batch_sent_total = Counter(
    'destination_batch_sent_total', 
    'Total number of batches sent to destinations',
    ['destination_name', 'organization_id', 'cc_pair_id', 'status']
)

# Response time metrics
destination_request_duration_seconds = Histogram(
    'destination_request_duration_seconds',
    'Time spent sending requests to destinations',
    ['destination_name', 'organization_id', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Error tracking
destination_errors_total = Counter(
    'destination_errors_total',
    'Total number of destination errors',
    ['destination_name', 'organization_id', 'error_type', 'cc_pair_id']
)

# Health status
destination_health_status = Gauge(
    'destination_health_status',
    'Destination health status (1=healthy, 0.5=degraded, 0=down)',
    ['destination_name', 'organization_id', 'target_id']
)

destination_last_health_check_timestamp = Gauge(
    'destination_last_health_check_timestamp',
    'Timestamp of last health check',
    ['destination_name', 'organization_id', 'target_id']
)

# =============================================================================
# CC-Pair Sync Metrics (following Onyx IndexAttempt patterns)
# =============================================================================

cc_pair_sync_attempts_total = Counter(
    'cc_pair_sync_attempts_total',
    'Total number of CC-Pair sync attempts',
    ['cc_pair_id', 'connector_source', 'destination_name', 'organization_id', 'status']
)

cc_pair_sync_duration_seconds = Histogram(
    'cc_pair_sync_duration_seconds',
    'Duration of CC-Pair sync operations',
    ['cc_pair_id', 'connector_source', 'destination_name', 'organization_id'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0]
)

cc_pair_documents_processed_total = Counter(
    'cc_pair_documents_processed_total',
    'Total documents processed by CC-Pairs',
    ['cc_pair_id', 'connector_source', 'destination_name', 'organization_id']
)

cc_pair_last_sync_timestamp = Gauge(
    'cc_pair_last_sync_timestamp',
    'Timestamp of last successful sync',
    ['cc_pair_id', 'connector_source', 'destination_name', 'organization_id']
)

cc_pair_active_syncs = Gauge(
    'cc_pair_active_syncs',
    'Number of currently active syncs',
    ['organization_id', 'destination_name']
)

# =============================================================================
# System Resource Metrics (extending Onyx memory monitoring)
# =============================================================================

destination_connection_pool_size = Gauge(
    'destination_connection_pool_size',
    'Current size of destination connection pools',
    ['destination_name', 'pool_type']
)

destination_rate_limit_remaining = Gauge(
    'destination_rate_limit_remaining',
    'Remaining rate limit for destination',
    ['destination_name', 'organization_id']
)

# =============================================================================
# Business Metrics (organization-level insights)
# =============================================================================

organization_destinations_count = Gauge(
    'organization_destinations_count',
    'Number of configured destinations per organization',
    ['organization_id']
)

organization_cc_pairs_count = Gauge(
    'organization_cc_pairs_count',
    'Number of CC-Pairs per organization',
    ['organization_id', 'status']
)

organization_daily_documents_synced = Counter(
    'organization_daily_documents_synced',
    'Daily document sync count per organization',
    ['organization_id', 'date']
)


# =============================================================================
# Metric Collection Helper Classes (following Onyx Metric pattern)
# =============================================================================

class DestinationMetricsCollector:
    """Collects and reports destination-specific metrics"""
    
    def __init__(self):
        self._active_requests: Dict[str, float] = {}
    
    def record_document_sent(
        self,
        destination_name: str,
        organization_id: str,
        cc_pair_id: str,
        count: int = 1,
        success: bool = True
    ) -> None:
        """Record documents sent to destination"""
        status = "success" if success else "error"
        destination_documents_sent_total.labels(
            destination_name=destination_name,
            organization_id=organization_id,
            cc_pair_id=str(cc_pair_id),
            status=status
        ).inc(count)
    
    def record_batch_sent(
        self,
        destination_name: str,
        organization_id: str,
        cc_pair_id: str,
        batch_size: int,
        success: bool = True
    ) -> None:
        """Record batch sent to destination"""
        status = "success" if success else "error"
        destination_batch_sent_total.labels(
            destination_name=destination_name,
            organization_id=organization_id,
            cc_pair_id=str(cc_pair_id),
            status=status
        ).inc()
        
        # Also record individual documents
        self.record_document_sent(
            destination_name, organization_id, cc_pair_id, batch_size, success
        )
    
    def start_request_timer(
        self,
        destination_name: str,
        organization_id: str,
        operation: str = "send"
    ) -> str:
        """Start timing a destination request"""
        request_id = f"{destination_name}_{organization_id}_{operation}_{time.time()}"
        self._active_requests[request_id] = time.time()
        return request_id
    
    def end_request_timer(
        self,
        request_id: str,
        destination_name: str,
        organization_id: str,
        operation: str = "send"
    ) -> float:
        """End timing a destination request and record metric"""
        if request_id not in self._active_requests:
            logger.warning(f"Request timer {request_id} not found")
            return 0.0
        
        duration = time.time() - self._active_requests.pop(request_id)
        
        destination_request_duration_seconds.labels(
            destination_name=destination_name,
            organization_id=organization_id,
            operation=operation
        ).observe(duration)
        
        return duration
    
    def record_error(
        self,
        destination_name: str,
        organization_id: str,
        error_type: str,
        cc_pair_id: Optional[str] = None
    ) -> None:
        """Record destination error"""
        destination_errors_total.labels(
            destination_name=destination_name,
            organization_id=organization_id,
            error_type=error_type,
            cc_pair_id=str(cc_pair_id) if cc_pair_id else "unknown"
        ).inc()
    
    def update_health_status(
        self,
        destination_name: str,
        organization_id: str,
        target_id: str,
        status: DestinationStatus
    ) -> None:
        """Update destination health status"""
        status_value = {
            DestinationStatus.HEALTHY: 1.0,
            DestinationStatus.DEGRADED: 0.5,
            DestinationStatus.DOWN: 0.0,
            DestinationStatus.UNKNOWN: -1.0
        }[status]
        
        destination_health_status.labels(
            destination_name=destination_name,
            organization_id=organization_id,
            target_id=target_id
        ).set(status_value)
        
        destination_last_health_check_timestamp.labels(
            destination_name=destination_name,
            organization_id=organization_id,
            target_id=target_id
        ).set(time.time())


class CCPairMetricsCollector:
    """Collects CC-Pair sync metrics (following Onyx IndexAttempt patterns)"""
    
    def __init__(self):
        self._active_syncs: Dict[str, float] = {}
    
    def start_sync(
        self,
        cc_pair_id: str,
        connector_source: str,
        destination_name: str,
        organization_id: str
    ) -> str:
        """Start tracking a CC-Pair sync"""
        sync_id = f"sync_{cc_pair_id}_{time.time()}"
        self._active_syncs[sync_id] = time.time()
        
        # Increment active syncs gauge
        cc_pair_active_syncs.labels(
            organization_id=organization_id,
            destination_name=destination_name
        ).inc()
        
        return sync_id
    
    def end_sync(
        self,
        sync_id: str,
        cc_pair_id: str,
        connector_source: str,
        destination_name: str,
        organization_id: str,
        success: bool = True,
        documents_processed: int = 0
    ) -> float:
        """End CC-Pair sync and record metrics"""
        if sync_id not in self._active_syncs:
            logger.warning(f"Sync {sync_id} not found in active syncs")
            return 0.0
        
        duration = time.time() - self._active_syncs.pop(sync_id)
        status = "success" if success else "error"
        
        # Record sync attempt
        cc_pair_sync_attempts_total.labels(
            cc_pair_id=str(cc_pair_id),
            connector_source=connector_source,
            destination_name=destination_name,
            organization_id=organization_id,
            status=status
        ).inc()
        
        # Record sync duration
        cc_pair_sync_duration_seconds.labels(
            cc_pair_id=str(cc_pair_id),
            connector_source=connector_source,
            destination_name=destination_name,
            organization_id=organization_id
        ).observe(duration)
        
        # Record documents processed
        if documents_processed > 0:
            cc_pair_documents_processed_total.labels(
                cc_pair_id=str(cc_pair_id),
                connector_source=connector_source,
                destination_name=destination_name,
                organization_id=organization_id
            ).inc(documents_processed)
        
        # Update last sync timestamp if successful
        if success:
            cc_pair_last_sync_timestamp.labels(
                cc_pair_id=str(cc_pair_id),
                connector_source=connector_source,
                destination_name=destination_name,
                organization_id=organization_id
            ).set(time.time())
        
        # Decrement active syncs gauge
        cc_pair_active_syncs.labels(
            organization_id=organization_id,
            destination_name=destination_name
        ).dec()
        
        return duration


# Global metric collectors (singleton pattern like Onyx)
destination_metrics = DestinationMetricsCollector()
cc_pair_metrics = CCPairMetricsCollector()


