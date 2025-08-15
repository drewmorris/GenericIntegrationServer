"""
Database initialization and startup utilities.
"""
import os
import logging
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


logger = logging.getLogger(__name__)


def initialize_database() -> None:
    """
    Initialize the database on application startup.
    This runs migrations automatically when the app starts.
    """
    try:
        logger.info("🔧 Initializing database...")
        
        # Check if database is available
        if not _database_available():
            logger.warning("⚠️  Database not available - skipping initialization")
            return
        
        # Run migrations
        _run_migrations()
        logger.info("✅ Database initialization complete")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # In production, you might want to raise this to prevent startup
        # For now, we'll log and continue to allow development without DB
        logger.warning("Continuing startup without database...")


def _database_available() -> bool:
    """Check if database is available."""
    try:
        database_url = _get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        engine.dispose()
        return True
        
    except Exception as e:
        logger.debug(f"Database not available: {e}")
        return False


def _get_database_url() -> str:
    """Get database URL from environment variables."""
    # Use sync URL for migrations (Alembic doesn't support async)
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db = os.getenv("POSTGRES_DB", "integration_server")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _run_migrations() -> None:
    """Run Alembic migrations."""
    database_url = _get_database_url()
    logger.info(f"Running migrations for: {database_url}")
    
    # Hide alembic info logs during migration
    logging.getLogger("alembic").setLevel(logging.WARNING)
    
    try:
        # Create Alembic configuration
        cfg = Config("backend/alembic.ini")
        cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Run migrations
        command.upgrade(cfg, "head")
        logger.info("✅ Database migrations completed")
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        raise
    finally:
        # Restore alembic logging
        logging.getLogger("alembic").setLevel(logging.INFO)
