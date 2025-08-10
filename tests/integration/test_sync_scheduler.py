import os
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# Ensure Docker daemon available, else skip
try:
    import docker  # type: ignore

    docker.from_env().ping()
except Exception:  # noqa: BLE001
    pytest.skip("Docker daemon not available", allow_module_level=True)

from sqlalchemy import select
from alembic import command
from alembic.config import Config


# Try importing containers
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


async def _create_profile(session, org_id, user_id):
    from backend.db import models as m

    profile = m.ConnectorProfile(
        id=os.urandom(16).hex(),
        organization_id=org_id,
        user_id=user_id,
        name="Test GDrive",
        source="google_drive",
        interval_minutes=1,
        next_run_at=datetime.utcnow() - timedelta(minutes=1),
        created_at=datetime.utcnow(),
    )
    session.add(profile)
    await session.commit()
    return profile


@pytest.mark.skipif(PostgresContainer is None or RedisContainer is None, reason="testcontainers libs missing")
async def test_scheduler_enqueues_and_creates_sync_run():  # noqa: D401
    with PostgresContainer("postgres:15-alpine") as pg, RedisContainer("redis:7-alpine") as redis:
        sync_pg = pg.get_connection_url()
        if hasattr(redis, "get_connection_url"):
            redis_url = redis.get_connection_url()  # type: ignore[attr-defined]
        else:
            host = redis.get_container_host_ip(); port = redis.get_exposed_port(6379)
            redis_url = f"redis://{host}:{port}/0"

        os.environ["REDIS_URL"] = redis_url
        _run_migrations(sync_pg)

        import re
        async_url = re.sub(r"^postgresql(\+[A-Za-z0-9_]+)?://", "postgresql+asyncpg://", sync_pg)
        engine = create_async_engine(async_url, future=True)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        # Insert org, user, profile
        async with Session() as sess:
            from backend.db import models as m

            org = m.Organization(id=os.urandom(16).hex(), name="OrgX", created_at=datetime.utcnow())
            user = m.User(id=os.urandom(16).hex(), organization_id=org.id, email="u@x.com", hashed_pw="x", role="member", created_at=datetime.utcnow())
            sess.add_all([org, user])
            await sess.commit()
            profile = await _create_profile(sess, org.id, user.id)  # noqa: F841  (unused)

        # Import orchestrator AFTER env vars set so Celery picks Redis URL
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
        from backend.orchestrator.scheduler import scan_due_profiles
        from backend.db.models import SyncRun

        # Start worker in background process
        from multiprocessing import Process

        def _worker():
            import os as _os
            _os.environ["CELERY_BROKER_URL"] = "memory://"
            _os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
            # parse and pass PG from sync_pg
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
            try:
                from backend.orchestrator import celery_app as _cel
                _cel.conf.broker_url = _os.environ.get("CELERY_BROKER_URL", "memory://")
                _cel.conf.result_backend = _os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")
                _cel.backend = _cel._get_backend()  # type: ignore[attr-defined]
                _cel.conf.task_ignore_result = True
            except Exception:
                pass
            # Reload DB session and rebind session factories in task modules
            try:
                import importlib
                import backend.db.session as s
                importlib.reload(s)
                import backend.orchestrator.task_utils as tu
                import backend.orchestrator.tasks as tasks
                tu.AsyncSessionLocal = s.AsyncSessionLocal  # type: ignore[attr-defined]
                tasks.AsyncSessionLocal = s.AsyncSessionLocal  # type: ignore[attr-defined]
            except Exception:
                pass
            # Ensure DB schema exists
            try:
                from alembic.config import Config as _Cfg
                from alembic import command as _cmd
                _cfg = _Cfg("backend/alembic.ini"); _cfg.set_main_option("sqlalchemy.url", sync_pg)
                _cmd.upgrade(_cfg, "head")
            except Exception:
                pass
            celery_app.worker_main([
                "worker",
                "--concurrency",
                "1",
                "--pool",
                "solo",
                "--loglevel",
                "INFO",
                "-Q",
                "default",
            ])

        worker_proc = Process(target=_worker)
        worker_proc.start()
        try:
            # Trigger scheduler task and poll for a run record
            scan_due_profiles.apply_async()
            for _ in range(40):
                async with Session() as verify_sess:
                    runs = (await verify_sess.execute(select(SyncRun))).scalars().all()
                    if runs:
                        break
                time.sleep(0.25)
            assert runs and runs[0].status in {"success", "running", "failure"}
        finally:
            worker_proc.terminate()
            worker_proc.join() 