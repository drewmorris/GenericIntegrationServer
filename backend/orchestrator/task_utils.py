from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import SyncRun, ConnectorProfile
from backend.db.session import AsyncSessionLocal
from backend.db.rls import set_current_org


async def run_with_syncrow(
    profile_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    runner: Callable[[AsyncSession], Awaitable[int]] | Callable[[AsyncSession], int],
) -> None:
    """Wrap connector run with SyncRun row creation and status updates.

    runner(session) should return int (records synced) or raise.
    """
    async with AsyncSessionLocal() as session:
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
        async with AsyncSessionLocal() as run_sess:
            await set_current_org(run_sess, org_id)
            records = await runner(run_sess) if callable(runner) else 0
        status = "success"
    except Exception:
        records = 0
        status = "failure"
        raise
    finally:
        async with AsyncSessionLocal() as finish_sess:
            await set_current_org(finish_sess, org_id)
            await finish_sess.execute(
                select(SyncRun).where(SyncRun.id == sync_run.id)
            )
            sync_run.finished_at = datetime.utcnow()
            sync_run.status = status
            sync_run.records_synced = records
            await finish_sess.commit() 