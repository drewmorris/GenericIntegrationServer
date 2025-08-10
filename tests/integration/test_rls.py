import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from alembic import command
from alembic.config import Config

# Skip if Docker daemon not available, to avoid failing when containers cannot start
try:
    import docker  # type: ignore

    docker.from_env().ping()
except Exception:  # noqa: BLE001
    import pytest  # ensure avail

    pytest.skip("Docker daemon not available", allow_module_level=True)

from backend.db.rls import set_current_org
from backend.auth.db_provider import DbAuthProvider
from backend.db import models  # noqa: F401 ensure models imported


@pytest.mark.asyncio
async def test_rls_isolation() -> None:  # noqa: D401
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        PostgresContainer = None  # type: ignore

    if PostgresContainer is None:
        pytest.skip("testcontainers not installed")

    pg = PostgresContainer("postgres:15-alpine")
    try:
        pg.start()
    except Exception as exc:  # noqa: F841  (unused var)
        pytest.skip("Docker not available for Testcontainers")
    try:
        sync_url = pg.get_connection_url()
        import re
        async_url = re.sub(r"^postgresql(\+[A-Za-z0-9_]+)?://", "postgresql+asyncpg://", sync_url)

        # run migrations
        alembic_cfg = Config("backend/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")

        # Main engine as superuser (for setup)
        engine = create_async_engine(async_url, future=True)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            provider = DbAuthProvider(session)
            # Org1 signup
            await provider.signup("a@example.com", "pw123456", org_name="Org1")
            # Org2 signup
            await provider.signup("b@example.com", "pw123456", org_name="Org2")
            await session.commit()
            # Clear any previously set org on this connection
            await session.execute(text("SELECT set_config('app.current_org', NULL, false)"))

        # create a non-superuser role for RLS verification
        async with async_session() as session:
            await session.execute(text("CREATE ROLE appuser LOGIN PASSWORD 'app'"))
            await session.execute(text("GRANT SELECT ON TABLE \"user\" TO appuser"))
            await session.commit()

        # fetch org ids
        async with async_session() as session:
            orgs = (await session.execute(select(models.Organization))).scalars().all()
            org1, org2 = orgs[0].id, orgs[1].id

        # Build a verification engine using the non-superuser
        import re as _re
        verify_url = _re.sub(r"//[^:]+:[^@]+@", "//appuser:app@", async_url)
        verify_engine = create_async_engine(verify_url, future=True)
        verify_session = async_sessionmaker(verify_engine, expire_on_commit=False)

        # Verify RLS: session with org1 sees only its user (as non-superuser)
        async with verify_session() as session_org1:
            # Use global (non-local) to survive across implicit transactions in CI
            await session_org1.execute(text("SELECT set_config('app.current_org', :org, false)"), {"org": str(org1)})
            users_org1 = (await session_org1.execute(select(models.User))).scalars().all()
            assert len(users_org1) == 1
            assert users_org1[0].email == "a@example.com"

        async with verify_session() as session_org2:
            await session_org2.execute(text("SELECT set_config('app.current_org', :org, false)"), {"org": str(org2)})
            users_org2 = (await session_org2.execute(select(models.User))).scalars().all()
            assert len(users_org2) == 1
            assert users_org2[0].email == "b@example.com"
    finally:
        pg.stop() 