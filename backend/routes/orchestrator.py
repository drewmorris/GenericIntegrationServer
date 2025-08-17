from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.orchestrator.tasks import sync_connector
from backend.db.session import get_db
from backend.deps import get_current_org_id

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])


@router.post(
    "/sync/{profile_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger immediate sync",
    description="Manually enqueue a Celery job to run the connector profile immediately instead of waiting for the scheduler.",
)
async def trigger_sync(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_org_id: str = Depends(get_current_org_id),
):
    # Verify profile exists and belongs to current org
    from backend.db.models import ConnectorProfile
    result = await db.execute(
        select(ConnectorProfile).where(
            ConnectorProfile.id == str(profile_id),
            ConnectorProfile.organization_id == current_org_id
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    task = sync_connector.delay(str(profile_id), str(profile.organization_id), str(profile.user_id))
    return {"task_id": task.id} 