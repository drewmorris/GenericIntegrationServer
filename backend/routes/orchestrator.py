from fastapi import APIRouter, status

from backend.orchestrator.tasks import sync_connector

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])


@router.post(
    "/sync/{profile_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger immediate sync",
    description="Manually enqueue a Celery job to run the connector profile immediately instead of waiting for the scheduler.",
)
async def trigger_sync(profile_id: int):
    # In a real implementation we'd look up the profile to pull user + org
    task = sync_connector.delay(str(profile_id), "00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000")
    return {"task_id": task.id} 