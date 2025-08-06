from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db.models import SyncRun

router = APIRouter(prefix="/sync_runs", tags=["SyncRuns"])


@router.get("/{profile_id}")
async def list_runs(profile_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SyncRun).where(SyncRun.profile_id == profile_id).order_by(SyncRun.started_at.desc()))
    return [run.model_dump() for run in result.scalars().all()] 