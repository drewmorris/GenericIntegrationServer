import os
import tempfile
import time
from datetime import datetime, timedelta

import pytest
import httpx
# Skip when Docker daemon not accessible
try:
    import docker  # type: ignore

    _client = docker.from_env()
    _client.ping()
except Exception:  # noqa: BLE001
    pytest.skip("Docker daemon not available", allow_module_level=True)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from alembic import command
from alembic.config import Config

try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
except ImportError:
    PostgresContainer = None  # type: ignore
    RedisContainer = None  # type: ignore

pytestmark = pytest.mark.asyncio


def _run_migrations(sync_url: str) -> None:
    cfg = Config("backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


async def _bootstrap_objects(sess):
    from backend.db import models as m
    import uuid

    org = m.Organization(id=uuid.uuid4(), name="OrgEnd", created_at=datetime.utcnow())
    user = m.User(id=uuid.uuid4(), organization_id=org.id, email="u@end.com", hashed_pw="x", role="member", created_at=datetime.utcnow())
    sess.add_all([org, user])
    await sess.commit()
    return org, user


@pytest.mark.skipif(PostgresContainer is None or RedisContainer is None, reason="testcontainers missing")
async def test_cleverbrag_and_csv_destinations(monkeypatch):
    with PostgresContainer("postgres:15-alpine") as pg, RedisContainer("redis:7-alpine") as redis:
        sync_pg = pg.get_connection_url()
        if hasattr(redis, "get_connection_url"):
            redis_url = redis.get_connection_url()  # type: ignore[attr-defined]
        else:
            host = redis.get_container_host_ip()
            port = redis.get_exposed_port(6379)
            redis_url = f"redis://{host}:{port}/0"
        os.environ["REDIS_URL"] = redis_url

        _run_migrations(sync_pg)
        import re
        async_url = re.sub(r"^postgresql(\+[A-Za-z0-9_]+)?://", "postgresql+asyncpg://", sync_pg)
        engine = create_async_engine(async_url, future=True)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        # --------------------------------------------------
        # CleverBrag destination test with httpx MockTransport
        # --------------------------------------------------
        calls: list[httpx.Request] = []

        async def handler(request):  # noqa: D401
            calls.append(request)
            return httpx.Response(202)

        transport = httpx.MockTransport(handler)
        monkeypatch.setattr("backend.destinations.cleverbrag.httpx.AsyncClient", lambda timeout=30: httpx.AsyncClient(transport=transport))
        monkeypatch.setenv("CLEVERBRAG_BASE_URL", "https://mock")

        async with Session() as sess:
            from backend.db import models as m
            org, user = await _bootstrap_objects(sess)
            profile = m.ConnectorProfile(
                id=os.urandom(16).hex(),
                organization_id=org.id,
                user_id=user.id,
                name="CB Profile",
                source="mock",
                interval_minutes=1,
                next_run_at=datetime.utcnow() - timedelta(minutes=1),
                connector_config={
                    "destination": "cleverbrag",
                    "cleverbrag": {"api_key": "dummy"},
                },
                created_at=datetime.utcnow(),
            )
            sess.add(profile)
            await sess.commit()
            profile_id = profile.id

        # start worker proc
        from backend.orchestrator import celery_app
        # Use in-memory broker/result to avoid network flakiness under act
        os.environ["CELERY_BROKER_URL"] = "memory://"
        os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
        celery_app.conf.broker_url = os.environ["CELERY_BROKER_URL"]
        celery_app.conf.result_backend = os.environ["CELERY_RESULT_BACKEND"]
        celery_app.conf.task_ignore_result = True
        try:
            celery_app.backend = celery_app._get_backend()  # type: ignore[attr-defined]
        except Exception:
            pass
        from multiprocessing import Process
        from backend.orchestrator.scheduler import scan_due_profiles
        from backend.db.models import SyncRun

        def _worker():
            import os as _os
            # Use in-memory Celery for broker/result inside worker
            _os.environ["CELERY_BROKER_URL"] = "memory://"
            _os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
            # Also pass Postgres settings for scheduler engine
            try:
                from urllib.parse import urlparse
                parsed = urlparse(sync_pg)
                _os.environ["POSTGRES_HOST"] = parsed.hostname or "localhost"
                _os.environ["POSTGRES_PORT"] = str(parsed.port or 5432)
                if parsed.username:
                    _os.environ["POSTGRES_USER"] = parsed.username
                if parsed.password:
                    _os.environ["POSTGRES_PASSWORD"] = parsed.password
                _os.environ["POSTGRES_DB"] = (parsed.path or "/integration_server").lstrip("/")
            except Exception:
                pass
            # Ensure broker/result are set inside child process as well
            try:
                from backend.orchestrator import celery_app as _cel
                _cel.conf.broker_url = _os.environ.get("CELERY_BROKER_URL", "memory://")
                _cel.conf.result_backend = _os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")
                _cel.backend = _cel._get_backend()  # type: ignore[attr-defined]
                _cel.conf.task_ignore_result = True
            except Exception:
                pass
            # Reload DB session and dependent modules to honor new POSTGRES_* env
            try:
                import importlib
                import backend.db.session as s
                importlib.reload(s)
                # Rebind AsyncSessionLocal in task modules
                import backend.orchestrator.task_utils as tu
                import backend.orchestrator.tasks as tasks
                tu.AsyncSessionLocal = s.AsyncSessionLocal  # type: ignore[attr-defined]
                tasks.AsyncSessionLocal = s.AsyncSessionLocal  # type: ignore[attr-defined]
            except Exception:
                pass
            # Run Alembic migrations to ensure tables exist in worker-target DB
            try:
                from alembic.config import Config as _Cfg
                from alembic import command as _cmd
                _cfg = _Cfg("backend/alembic.ini"); _cfg.set_main_option("sqlalchemy.url", sync_pg)
                _cmd.upgrade(_cfg, "head")
            except Exception:
                pass
            celery_app.worker_main(["worker", "--concurrency", "1", "--pool", "solo", "--loglevel", "INFO", "-Q", "default"])

        p = Process(target=_worker)
        p.start()
        try:
            scan_due_profiles.apply_async()
            # poll up to ~10s for CleverBrag call
            for _ in range(40):
                if len(calls) >= 1:
                    break
                time.sleep(0.25)
            assert len(calls) == 1
            async with Session() as ver:
                runs = (await ver.execute(select(SyncRun).where(SyncRun.profile_id == profile_id))).scalars().all()
                assert runs and runs[0].status == "success"
        finally:
            p.terminate(); p.join()

        # --------------------------------------------------
        # CSV dump destination test
        # --------------------------------------------------
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("CSV_DUMP_DIR", tmpdir)
            async with Session() as sess:
                from backend.db import models as m
                profile_csv = m.ConnectorProfile(
                    id=os.urandom(16).hex(),
                    organization_id=org.id,
                    user_id=user.id,
                    name="CSV Profile",
                    source="mock",
                    interval_minutes=1,
                    next_run_at=datetime.utcnow() - timedelta(minutes=1),
                    connector_config={
                        "destination": "csv",
                    },
                    created_at=datetime.utcnow(),
                )
                sess.add(profile_csv)
                await sess.commit()
                csv_profile_id = profile_csv.id

            p2 = Process(target=_worker)
            p2.start()
            try:
                scan_due_profiles.apply_async()
                for _ in range(40):
                    if any(os.listdir(tmpdir)):
                        break
                    time.sleep(0.25)
                # csv file written?
                assert any(os.listdir(tmpdir)), "CSV dump dir should contain at least one file"
                async with Session() as ver2:
                    runs = (await ver2.execute(select(SyncRun).where(SyncRun.profile_id == csv_profile_id))).scalars().all()
                    assert runs and runs[0].status == "success"
            finally:
                p2.terminate(); p2.join() 