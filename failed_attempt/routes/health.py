"""
Health check and monitoring endpoints for database and application status.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from backend.db.monitoring import run_health_checks, get_database_metrics, db_monitor
from backend.db.session import health_check as db_health_check, get_pool_status

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="Basic health check")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    
    Returns simple status for load balancers and monitoring systems.
    """
    is_healthy = await db_health_check()
    
    if is_healthy:
        return {"status": "healthy", "message": "Service is operational"}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is unhealthy"
        )


@router.get("/detailed", summary="Detailed health check")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with comprehensive system status.
    
    Includes database connectivity, connection pool status,
    performance metrics, and error rates.
    """
    return await run_health_checks()


@router.get("/database", summary="Database-specific health check")
async def database_health() -> Dict[str, Any]:
    """
    Database-specific health check and metrics.
    
    Returns detailed information about database performance,
    connection pool status, and query metrics.
    """
    is_healthy = await db_health_check()
    metrics = await get_database_metrics()
    pool_status = get_pool_status()
    database_info = await db_monitor.get_database_info()
    
    return {
        "healthy": is_healthy,
        "metrics": metrics.to_dict(),
        "pool_status": pool_status,
        "database_info": database_info,
        "slow_queries": [
            {
                "query": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                "avg_time": q.avg_time,
                "execution_count": q.execution_count,
            }
            for q in db_monitor.get_slow_queries(5)
        ],
        "frequent_queries": [
            {
                "query": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                "execution_count": q.execution_count,
                "avg_time": q.avg_time,
            }
            for q in db_monitor.get_frequent_queries(5)
        ],
    }


@router.get("/metrics", summary="Application metrics")
async def application_metrics() -> Dict[str, Any]:
    """
    Application performance metrics.
    
    Returns metrics suitable for monitoring systems like Prometheus.
    """
    metrics = await get_database_metrics()
    pool_status = get_pool_status()
    
    return {
        "database": {
            "pool_size": pool_status["pool_size"],
            "checked_out_connections": pool_status["checked_out"],
            "checked_in_connections": pool_status["checked_in"],
            "overflow_connections": pool_status["overflow"],
            "invalid_connections": pool_status["invalid"],
            "active_connections": metrics.active_connections,
            "total_queries": metrics.query_count,
            "avg_query_time_seconds": metrics.avg_query_time,
            "slow_queries": metrics.slow_queries,
            "error_count": metrics.errors,
            "uptime_seconds": metrics.uptime_seconds,
        }
    }


@router.get("/readiness", summary="Readiness probe")
async def readiness_probe() -> Dict[str, str]:
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the service is ready to receive traffic.
    This includes database connectivity and essential services.
    """
    try:
        # Check database connectivity
        is_db_healthy = await db_health_check()
        
        if not is_db_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not ready"
            )
        
        # Check connection pool health
        pool_status = get_pool_status()
        pool_utilization = (pool_status["checked_out"] / pool_status["pool_size"]) * 100
        
        if pool_utilization > 95:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Connection pool exhausted"
            )
        
        return {"status": "ready", "message": "Service is ready to receive traffic"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/liveness", summary="Liveness probe")
async def liveness_probe() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    
    Checks if the service is alive and should not be restarted.
    This is a lightweight check that doesn't depend on external services.
    """
    return {"status": "alive", "message": "Service is alive"}

