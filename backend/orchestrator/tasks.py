from __future__ import annotations

from celery.utils.log import get_task_logger

# type: ignore
import uuid
from backend.orchestrator import celery_app
from backend.destinations import get_destination
from backend.db.rls import set_current_org
from backend.db.session import AsyncSessionLocal as _AsyncSessionLocal
from sqlalchemy import select
from backend.db import models as m

# Expose AsyncSessionLocal so tests can monkeypatch it easily
AsyncSessionLocal = _AsyncSessionLocal  # noqa: N816

# noqa
from backend.orchestrator.task_utils import run_with_syncrow

logger = get_task_logger(__name__)


@celery_app.task(
    name="orchestrator.sync_dummy",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def sync_connector(self, connector_profile_id: str, user_id: str, org_id: str) -> str:  # noqa: D401
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

    coro = run_with_syncrow(
        uuid.UUID(connector_profile_id), uuid.UUID(org_id), uuid.UUID(user_id), _runner
    )
    try:
        import asyncio as _asyncio
        loop = _asyncio.get_running_loop()
    except RuntimeError:
        loop = None  # no running loop
    if loop is None:
        import asyncio as _asyncio
        _asyncio.run(coro)
    else:
        # We're already inside an event loop (e.g. pytest-asyncio). Run the coroutine in
        # a dedicated thread so we can await its completion without nesting event loops.
        import threading, asyncio as _asyncio

        result_holder: list[Exception | None] = [None]

        def _thread_runner():  # noqa: D401
            try:
                _asyncio.run(coro)
            except Exception as exc:  # noqa: BLE001
                result_holder[0] = exc

        t = threading.Thread(target=_thread_runner, daemon=True)
        t.start()
        t.join()
        if result_holder[0] is not None:
            raise result_holder[0]
    return "ok"

# Expose Celery retry settings for unit tests
sync_connector.max_retries = 5  # type: ignore[attr-defined]
sync_connector.retry_backoff = True  # type: ignore[attr-defined] 