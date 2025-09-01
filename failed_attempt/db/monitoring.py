"""
Database monitoring, metrics, and health checks for production observability.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.db.session import engine, AsyncSessionLocal, get_pool_status

logger = logging.getLogger(__name__)


@dataclass
class DatabaseMetrics:
    """Database performance and health metrics."""
    timestamp: datetime
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int
    active_connections: int
    query_count: int
    avg_query_time: float
    slow_queries: int
    errors: int
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class QueryMetrics:
    """Individual query performance metrics."""
    query_hash: str
    query_text: str
    execution_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    last_executed: datetime


class DatabaseMonitor:
    """
    Database monitoring and metrics collection system.
    
    Provides real-time insights into database performance,
    connection pool health, and query performance.
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.error_count = 0
        self.total_queries = 0
        self.total_query_time = 0.0
        self.slow_query_threshold = 1.0  # seconds
        self.slow_queries = 0
    
    async def get_current_metrics(self) -> DatabaseMetrics:
        """Get current database metrics."""
        pool_status = get_pool_status()
        
        # Get active connections from PostgreSQL
        active_connections = await self._get_active_connections()
        
        avg_query_time = (
            self.total_query_time / self.total_queries
            if self.total_queries > 0 else 0.0
        )
        
        return DatabaseMetrics(
            timestamp=datetime.utcnow(),
            pool_size=pool_status["pool_size"],
            checked_in=pool_status["checked_in"],
            checked_out=pool_status["checked_out"],
            overflow=pool_status["overflow"],
            invalid=pool_status["invalid"],
            active_connections=active_connections,
            query_count=self.total_queries,
            avg_query_time=avg_query_time,
            slow_queries=self.slow_queries,
            errors=self.error_count,
            uptime_seconds=time.time() - self.start_time,
        )
    
    async def _get_active_connections(self) -> int:
        """Get number of active connections from PostgreSQL."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT count(*) 
                        FROM pg_stat_activity 
                        WHERE state = 'active' 
                        AND application_name = 'integration_server'
                    """)
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to get active connections: {e}")
            return 0
    
    def record_query(self, query_text: str, execution_time: float):
        """Record query execution metrics."""
        self.total_queries += 1
        self.total_query_time += execution_time
        
        if execution_time > self.slow_query_threshold:
            self.slow_queries += 1
            logger.warning(f"Slow query detected ({execution_time:.3f}s): {query_text[:100]}...")
        
        # Track individual query performance
        query_hash = str(hash(query_text))
        if query_hash in self.query_metrics:
            metrics = self.query_metrics[query_hash]
            metrics.execution_count += 1
            metrics.total_time += execution_time
            metrics.avg_time = metrics.total_time / metrics.execution_count
            metrics.min_time = min(metrics.min_time, execution_time)
            metrics.max_time = max(metrics.max_time, execution_time)
            metrics.last_executed = datetime.utcnow()
        else:
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=query_hash,
                query_text=query_text[:500],  # Truncate long queries
                execution_count=1,
                total_time=execution_time,
                avg_time=execution_time,
                min_time=execution_time,
                max_time=execution_time,
                last_executed=datetime.utcnow(),
            )
    
    def record_error(self, error: Exception):
        """Record database error."""
        self.error_count += 1
        logger.error(f"Database error recorded: {error}")
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get slowest queries by average execution time."""
        return sorted(
            self.query_metrics.values(),
            key=lambda q: q.avg_time,
            reverse=True
        )[:limit]
    
    def get_frequent_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get most frequently executed queries."""
        return sorted(
            self.query_metrics.values(),
            key=lambda q: q.execution_count,
            reverse=True
        )[:limit]
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive database health check.
        
        Returns detailed health information including:
        - Connection pool status
        - Database connectivity
        - Performance metrics
        - Error rates
        """
        health_status: Dict[str, Any] = {
            "healthy": True,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check database connectivity
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            health_status["checks"]["connectivity"] = {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            health_status["healthy"] = False
            health_status["checks"]["connectivity"] = {"status": "unhealthy", "message": f"Database connection failed: {e}"}
        
        # Check connection pool health
        pool_status = get_pool_status()
        pool_utilization = (pool_status["checked_out"] / pool_status["pool_size"]) * 100
        
        if pool_utilization > 90:
            health_status["healthy"] = False
            health_status["checks"]["pool"] = {"status": "critical", "message": f"Pool utilization critical: {pool_utilization:.1f}%"}
        elif pool_utilization > 70:
            health_status["checks"]["pool"] = {"status": "warning", "message": f"Pool utilization high: {pool_utilization:.1f}%"}
        else:
            health_status["checks"]["pool"] = {"status": "healthy", "message": f"Pool utilization normal: {pool_utilization:.1f}%"}
        
        # Check error rate
        error_rate = (self.error_count / max(self.total_queries, 1)) * 100
        if error_rate > 5:
            health_status["healthy"] = False
            health_status["checks"]["errors"] = {"status": "critical", "message": f"High error rate: {error_rate:.1f}%"}
        elif error_rate > 1:
            health_status["checks"]["errors"] = {"status": "warning", "message": f"Elevated error rate: {error_rate:.1f}%"}
        else:
            health_status["checks"]["errors"] = {"status": "healthy", "message": f"Error rate normal: {error_rate:.1f}%"}
        
        # Add metrics
        health_status["metrics"] = (await self.get_current_metrics()).to_dict()
        
        return health_status
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get detailed database information."""
        try:
            async with AsyncSessionLocal() as session:
                # Get PostgreSQL version
                version_result = await session.execute(text("SELECT version()"))
                version = version_result.scalar()
                
                # Get database size
                size_result = await session.execute(
                    text("SELECT pg_size_pretty(pg_database_size(current_database()))")
                )
                database_size = size_result.scalar()
                
                # Get table count
                table_result = await session.execute(
                    text("""
                        SELECT count(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                )
                table_count = table_result.scalar()
                
                return {
                    "version": version,
                    "database_size": database_size,
                    "table_count": table_count,
                    "connection_info": {
                        "host": engine.url.host,
                        "port": engine.url.port,
                        "database": engine.url.database,
                        "username": engine.url.username,
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}


# Global database monitor instance
db_monitor = DatabaseMonitor()


async def run_health_checks() -> Dict[str, Any]:
    """Run all database health checks and return results."""
    return await db_monitor.health_check()


async def get_database_metrics() -> DatabaseMetrics:
    """Get current database metrics."""
    return await db_monitor.get_current_metrics()


def record_query_execution(query_text: str, execution_time: float):
    """Record query execution for monitoring."""
    db_monitor.record_query(query_text, execution_time)


def record_database_error(error: Exception):
    """Record database error for monitoring."""
    db_monitor.record_error(error)
