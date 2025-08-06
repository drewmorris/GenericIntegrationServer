from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from backend.settings import get_settings
from backend.db.models import ConnectorProfile
from backend.orchestrator import celery_app
from backend.orchestrator.tasks import sync_dummy

settings = get_settings()
DB_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@"
    f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

engine = create_async_engine(DB_URL, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="orchestrator.scan_due_profiles")
async def scan_due_profiles() -> None:  # noqa: D401
    async with SessionLocal() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(ConnectorProfile).where(
                (ConnectorProfile.next_run_at == None)  # noqa: E711
                | (ConnectorProfile.next_run_at <= now)
            )
        )
        due_profiles = result.scalars().all()

        for profile in due_profiles:
            sync_dummy.delay(profile.id, str(profile.user_id), str(profile.organization_id))
            profile.next_run_at = now + timedelta(minutes=profile.interval_minutes)

        await session.commit() 