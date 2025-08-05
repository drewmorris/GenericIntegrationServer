from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import create_engine
from alembic import context

from backend.db.base import Base
from backend.db import models  # noqa: F401  # ensure models are imported
from backend.db.session import DATABASE_URL

config = context.config  # type: ignore[attr-defined]
fileConfig(config.config_file_name)  # type: ignore[arg-type]

config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)
    with connectable.connect() as connection:  # type: Connection
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 