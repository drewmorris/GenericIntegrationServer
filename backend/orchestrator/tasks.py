from __future__ import annotations

from celery.utils.log import get_task_logger

# type: ignore
import uuid
from backend.orchestrator import celery_app

# noqa
from backend.orchestrator.task_utils import run_with_syncrow

logger = get_task_logger(__name__)


@celery_app.task(name="orchestrator.sync_dummy")
def sync_connector(connector_profile_id: str, user_id: str, org_id: str) -> str:  # noqa: D401
    logger.info("Starting sync task profile=%s user=%s org=%s", connector_profile_id, user_id, org_id)

    async def _runner(session):  # dummy logic until real connector
        await session.run_sync(lambda _: None)
        return 0

    import asyncio

    asyncio.run(run_with_syncrow(uuid.UUID(connector_profile_id), uuid.UUID(org_id), uuid.UUID(user_id), _runner))
    return "ok" 