from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db.models import SyncRun

router = APIRouter(prefix="/sync_runs", tags=["SyncRuns"])


@router.get(
    "/{profile_id}",
    summary="List sync runs for profile",
    description="Return historical sync run rows for the given connector profile (visible to the current org).",
)
async def list_runs(profile_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SyncRun).where(SyncRun.profile_id == profile_id).order_by(SyncRun.started_at.desc())
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "records_synced": r.records_synced,
        }
        for r in runs
    ] 