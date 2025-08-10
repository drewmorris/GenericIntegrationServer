from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

# Make overridable session factory for tests
AsyncSessionLocal = None  # type: ignore[assignment]

from backend.db.models import SyncRun
from backend.db.rls import set_current_org
# Build session factory lazily each call so CURRENT environment variables are honoured.
from backend.settings import get_settings
import inspect


# Internal helper to build session factory based on current env settings
def _create_session_factory() -> async_sessionmaker[AsyncSession]:  # noqa: D401
    # Ensure we pick up most recent env vars (tests set these at runtime)
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except AttributeError:
        pass
    settings = get_settings()
    db_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@"
        f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    engine = create_async_engine(db_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def run_with_syncrow(
    profile_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    runner: Callable[[AsyncSession], Awaitable[int]] | Callable[[AsyncSession], int],
) -> None:
    """Wrap connector run with SyncRun row creation and status updates.

    runner(session) should return int (records synced) or raise.
    """
    SessionLocal = AsyncSessionLocal if callable(AsyncSessionLocal) else _create_session_factory()
    async with SessionLocal() as session:
        await set_current_org(session, org_id)
        sync_run = SyncRun(
            id=uuid.uuid4(),
            profile_id=profile_id,
            started_at=datetime.utcnow(),
            status="running",
        )
        session.add(sync_run)
        await session.commit()

    try:
        async with SessionLocal() as run_sess:
            await set_current_org(run_sess, org_id)
            if inspect.iscoroutinefunction(runner):
                records = await runner(run_sess)
            else:
                records = runner(run_sess)
            # update success immediately so other sessions can observe it
            sync_run.finished_at = datetime.utcnow()
            sync_run.status = "success"
            sync_run.records_synced = records
            if hasattr(run_sess, "merge"):
                await run_sess.merge(sync_run)  # type: ignore[attr-defined]
            if hasattr(run_sess, "commit"):
                await run_sess.commit()
    finally:
        async with SessionLocal() as finish_sess:
            await set_current_org(finish_sess, org_id)
            if hasattr(finish_sess, "merge"):
                await finish_sess.merge(sync_run)  # type: ignore[attr-defined]
            if hasattr(finish_sess, "commit"):
                await finish_sess.commit() 