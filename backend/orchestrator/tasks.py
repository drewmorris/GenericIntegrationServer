from __future__ import annotations

from celery.utils.log import get_task_logger

# type: ignore
import uuid
from backend.orchestrator import celery_app
from backend.destinations import get_destination
from backend.db.session import AsyncSessionLocal
from backend.db.rls import set_current_org
from sqlalchemy import select
from backend.db import models as m

# noqa
from backend.orchestrator.task_utils import run_with_syncrow

logger = get_task_logger(__name__)


@celery_app.task(name="orchestrator.sync_dummy")
def sync_connector(connector_profile_id: str, user_id: str, org_id: str) -> str:  # noqa: D401
    logger.info("Starting sync task profile=%s user=%s org=%s", connector_profile_id, user_id, org_id)

    import asyncio

    async def _runner(session):
        await set_current_org(session, uuid.UUID(org_id))
        profile = (
            await session.execute(
                select(m.ConnectorProfile).where(m.ConnectorProfile.id == connector_profile_id)
            )
        ).scalar_one()

        # --------------------------------------------------
        # Use actual Onyx connector runtime when possible
        # --------------------------------------------------
        docs: list[dict]
        try:
            from connectors.onyx.connectors.connector_runner import ConnectorRunner  # type: ignore
            from connectors.onyx.connectors.mock_connector.connector import MockConnector, MockConnectorCheckpoint  # type: ignore
            import datetime as _dt

            if profile.source == "mock_source":
                # Basic demo using MockConnector (does not hit external APIs)
                connector = MockConnector(mock_server_host="localhost", mock_server_port=9999)
                connector.load_credentials(profile.connector_config or {})
                runner = ConnectorRunner(connector, batch_size=10, include_permissions=False, time_range=(_dt.datetime.utcnow(), _dt.datetime.utcnow()))
                batch_gen = runner.run(MockConnectorCheckpoint())
                docs = []
                for batch, failure, _ in batch_gen:  # type: ignore[assignment]
                    if batch:
                        docs.extend([d.model_dump(mode="json") for d in batch])
                if not docs:
                    # fall back if no docs
                    docs.append({"id": profile.id, "raw_text": "mock doc"})
            else:
                # TODO: map other sources → real connectors (Phase 6)
                docs = [{"id": profile.id, "raw_text": "placeholder doc"}]
        except Exception:  # noqa: BLE001
            # Fallback to placeholder document on any failure / missing deps
            docs = [
                {
                    "id": profile.id,
                    "metadata": {"profile_name": profile.name},
                    "raw_text": "This is a placeholder document from integration server.",
                }
            ]

        dest_name = (profile.connector_config or {}).get("destination", "cleverbrag")
        dest_cls = get_destination(dest_name)
        dest = dest_cls()
        await dest.send(payload=docs, profile_config=profile.connector_config or {})
        return len(docs)

    asyncio.run(run_with_syncrow(uuid.UUID(connector_profile_id), uuid.UUID(org_id), uuid.UUID(user_id), _runner))
    return "ok" 