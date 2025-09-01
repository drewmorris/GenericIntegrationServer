from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

# Import Base and models in a migration-safe way (avoid async imports)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# Create a simple sync base for migrations (avoid AsyncAttrs)
class MigrationBase(DeclarativeBase):
    metadata = MetaData()

# Import models to build metadata, but catch any async import issues
try:
    from backend.db import models  # noqa: F401
    # Use the actual Base metadata if available
    from backend.db.base import Base as ActualBase
    target_metadata = ActualBase.metadata
except ImportError as e:
    print(f"Warning: Could not import models for migrations: {e}")
    # Fallback to empty metadata
    target_metadata = MigrationBase.metadata

# Build DATABASE_URL for sync connection (Alembic needs sync, not async)
import os
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "integration_server")

# Allow override via DATABASE_URL environment variable, but ensure it's sync (psycopg2)
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
# Remove async driver specifier if present
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

# Load logging config if present and valid
config = context.config  # type: ignore[attr-defined]
try:
    if config.config_file_name:
        fileConfig(config.config_file_name)  # type: ignore[arg-type]
except (KeyError, ValueError):
    # Minimal ini in test may lack [formatters]; skip logging config
    pass

# Respect URL provided by external Config (tests); fallback to app DATABASE_URL
existing_url = config.get_main_option("sqlalchemy.url")
if not existing_url:
    config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))

# target_metadata is set above in the try/except block

def run_migrations_offline() -> None:
    context.configure(url=str(config.get_main_option("sqlalchemy.url")), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    url = str(config.get_main_option("sqlalchemy.url"))
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:  # type: Connection
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 