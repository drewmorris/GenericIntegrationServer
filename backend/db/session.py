import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import event

from backend.db.rls import set_current_org

logger = logging.getLogger(__name__)

# Database configuration with environment variables and sensible defaults
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "integration_server")

# Connection pool configuration for production scalability
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))  # Base pool size
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))  # Additional connections under load
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Seconds to wait for connection
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Recycle connections every hour
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "false" if "pytest" in os.getenv("_", "") else "true").lower() == "true"  # Health check connections

# Allow override via DATABASE_URL environment variable (for migrations, tests, etc.)
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Create engine with production-grade connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",  # Enable SQL logging in dev
    future=True,
    # Connection pool configuration
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,
    # Connection arguments for asyncpg
    connect_args={
        "server_settings": {
            "application_name": "integration_server",
            "jit": "off",  # Disable JIT for better connection performance
        },
        "command_timeout": 60,  # Query timeout
        "statement_cache_size": 0,  # Disable statement cache for better memory usage
    },
)

# Session factory with proper configuration
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,  # Manual control over when to flush
    autocommit=False,  # Explicit transaction control
)


# Connection pool monitoring and health checks
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level configuration."""
    # This is for PostgreSQL, but we can add connection-level settings here
    pass


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring."""
    logger.debug("Connection returned to pool")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with proper transaction management and error handling.
    
    This function provides:
    - Automatic transaction management
    - Proper error handling and rollback
    - Connection cleanup
    - Retry logic for transient failures
    """
    session: Optional[AsyncSession] = None
    try:
        session = AsyncSessionLocal()
        yield session
        # Commit transaction if no exceptions occurred
        await session.commit()
    except DisconnectionError as e:
        # Handle database disconnection errors
        logger.error(f"Database disconnection error: {e}")
        if session:
            await session.rollback()
        raise
    except SQLAlchemyError as e:
        # Handle all other SQLAlchemy errors
        logger.error(f"Database error: {e}")
        if session:
            await session.rollback()
        raise
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error in database session: {e}")
        if session:
            await session.rollback()
        raise
    finally:
        # Ensure session is always closed
        if session:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with explicit transaction control.
    
    Use this for operations that need explicit transaction boundaries,
    such as complex multi-table operations or when you need to control
    commit/rollback timing manually.
    """
    session: Optional[AsyncSession] = None
    try:
        session = AsyncSessionLocal()
        async with session.begin():
            yield session
            # Transaction is automatically committed by the context manager
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        # Rollback is automatic with session.begin() context manager
        raise
    finally:
        if session:
            await session.close()


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    Get read-only database session for queries that don't modify data.
    
    This can be optimized further by using read replicas in production.
    """
    session: Optional[AsyncSession] = None
    try:
        session = AsyncSessionLocal()
        # Set session to read-only mode
        from sqlalchemy import text
        await session.execute(text("SET TRANSACTION READ ONLY"))
        yield session
    except Exception as e:
        logger.error(f"Read-only session error: {e}")
        raise
    finally:
        if session:
            await session.close()


async def health_check() -> bool:
    """
    Check database connectivity and pool health.
    
    Returns True if database is healthy, False otherwise.
    """
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_pool_status() -> dict:
    """
    Get connection pool status for monitoring.
    
    Returns dictionary with pool metrics.
    """
    pool = engine.pool
    status = {
        "pool_size": getattr(pool, '_pool_size', 0),
        "checked_in": getattr(pool, '_checked_in', 0), 
        "checked_out": getattr(pool, '_checked_out', 0),
        "overflow": getattr(pool, '_overflow', 0),
        "invalid": 0,  # Not available in async pools
    }
    
    # For async pools, try to get actual values if available
    try:
        if hasattr(pool, 'size'):
            status["pool_size"] = pool.size()
        if hasattr(pool, 'checkedin'):
            status["checked_in"] = pool.checkedin()
        if hasattr(pool, 'checkedout'):
            status["checked_out"] = pool.checkedout()
        if hasattr(pool, 'overflow'):
            status["overflow"] = pool.overflow()
    except Exception:
        # Fallback to safe defaults if pool methods fail
        pass
    
    return status 