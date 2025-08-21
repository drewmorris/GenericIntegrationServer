"""
Prometheus metrics endpoint for destination and CC-Pair monitoring
Extends Onyx's existing Prometheus integration
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/prometheus",
    summary="Prometheus metrics endpoint",
    description="Returns Prometheus-formatted metrics for destination and CC-Pair monitoring",
)
async def get_prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint that includes all destination and CC-Pair metrics
    
    This endpoint extends Onyx's existing metrics with our destination-specific metrics:
    - destination_documents_sent_total
    - destination_request_duration_seconds  
    - destination_health_status
    - cc_pair_sync_attempts_total
    - cc_pair_sync_duration_seconds
    - And many more...
    """
    try:
        # Generate Prometheus metrics
        metrics_data = generate_latest()
        
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache", 
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}\n",
            media_type=CONTENT_TYPE_LATEST,
            status_code=500
        )


@router.get(
    "/health",
    summary="Metrics endpoint health check",
    description="Simple health check for the metrics endpoint",
)
async def metrics_health() -> dict:
    """Health check for metrics endpoint"""
    return {
        "status": "healthy",
        "metrics_available": True,
        "endpoint": "/metrics/prometheus"
    }
