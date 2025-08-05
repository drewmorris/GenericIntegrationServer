import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.engine.url import URL

from backend.db.rls import set_current_org

from typing import Annotated
import uuid
from fastapi import Depends
from backend.deps import get_org_id


DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "integration_server")

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db(org_id: Annotated[uuid.UUID, Depends(get_org_id)] | None = None) -> AsyncSession:  # noqa: D401
    async with AsyncSessionLocal() as session:
        if org_id is not None:
            await set_current_org(session, org_id)
        yield session 