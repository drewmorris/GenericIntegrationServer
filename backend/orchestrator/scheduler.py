from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import asyncio
from sqlalchemy import select

from backend.settings import get_settings
from backend.db.models import ConnectorProfile, SyncRun
from backend.orchestrator import celery_app
from backend.orchestrator.tasks import sync_connector as sync_dummy

# Lazily created session factory so env vars set at runtime are honored,
# and tests can monkeypatch `SessionLocal`.
SessionLocal = None  # type: ignore[assignment]


def _ensure_session_factory():
    global SessionLocal
    if SessionLocal is None or not callable(SessionLocal):  # type: ignore[truthy-function]
        settings = get_settings()
        db_url = (
            f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@"
            f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        engine = create_async_engine(db_url, future=True)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def _scan_due_profiles_impl() -> None:
    _ensure_session_factory()
    async with SessionLocal() as session:  # type: ignore[misc]
        now = datetime.utcnow()
        result = await session.execute(
            select(ConnectorProfile).where(
                (ConnectorProfile.next_run_at.is_(None))
                | (ConnectorProfile.next_run_at <= now)
            )
        )
        due_profiles = result.scalars().all()

        for profile in due_profiles:
            existing_res = await session.execute(
                select(SyncRun).where(
                    (SyncRun.profile_id == profile.id) & (SyncRun.status.in_(["running", "pending"]))
                )
            )
            existing_runs = existing_res.scalars().all()
            if existing_runs and isinstance(existing_runs[0], SyncRun):
                continue
            sync_dummy.delay(str(profile.id), str(profile.user_id), str(profile.organization_id))
            profile.next_run_at = now + timedelta(minutes=profile.interval_minutes)

        await session.commit()


@celery_app.task(name="orchestrator.scan_due_profiles")
def scan_due_profiles() -> None:  # noqa: D401
    asyncio.run(_scan_due_profiles_impl())

# Async alias used by unit tests that run inside an event loop
async def scan_due_profiles_async() -> None:
    await _scan_due_profiles_impl() 