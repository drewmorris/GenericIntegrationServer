from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from backend.orchestrator import tasks as orchestrator_tasks


class _FakeDest:  # noqa: D401
    def __init__(self) -> None:
        self.sent_payloads: list[list[dict]] = []

    async def send(self, *, payload: list[dict], profile_config: dict | None) -> None:  # noqa: D401
        self.sent_payloads.append(payload)


class _FakeSession:  # minimal async session
    def __init__(self, profile):
        self._profile = profile
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, *args, **kwargs):  # noqa: D401
        # Return object with .scalar_one()
        class _Res:
            def __init__(self, obj):
                self._obj = obj

            def scalar_one(self):  # noqa: D401
                return self._obj

        return _Res(self._profile)

    async def commit(self):  # noqa: D401
        self.committed = True

    def add(self, _obj):
        return None


def test_sync_connector_task(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D401
    profile = SimpleNamespace(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        name="demo",
        source="mock_source",
        connector_config={},
    )

    # Fake session
    fake_session_factory = lambda: _FakeSession(profile)
    monkeypatch.setattr(orchestrator_tasks, "AsyncSessionLocal", fake_session_factory)
    import backend.db.session as _db_sess
    monkeypatch.setattr(_db_sess, "AsyncSessionLocal", fake_session_factory)

    # No-op the RLS helper to avoid executing SQL
    import backend.db.rls as _rls
    async def _noop_set_current_org(session, org_id):  # noqa: D401
        return None
    monkeypatch.setattr(_rls, "set_current_org", _noop_set_current_org)
    import backend.orchestrator.task_utils as _tu
    monkeypatch.setattr(_tu, "AsyncSessionLocal", fake_session_factory)
    monkeypatch.setattr(_tu, "set_current_org", _noop_set_current_org)

    # Fake destination registry
    fake_dest = _FakeDest()

    def _fake_get_destination(name: str):  # noqa: D401
        assert name == "cleverbrag"
        return lambda: fake_dest

    monkeypatch.setattr(orchestrator_tasks, "get_destination", _fake_get_destination)

    # Patch ConnectorRunner to bypass real connector runtime and simply return one doc
    import types, sys
    dummy_mod = types.ModuleType("connector_runner")

    class _DummyRunner:  # noqa: D401
        def __init__(self, *a, **kw):
            pass

        def run(self, _cp):  # noqa: D401
            return [([SimpleNamespace(model_dump=lambda mode: {"id": "d1"})], [], None)]

    dummy_mod.ConnectorRunner = _DummyRunner  # type: ignore[attr-defined]
    sys.modules["connectors.onyx.connectors.connector_runner"] = dummy_mod

    # Run task
    result = orchestrator_tasks.sync_connector(profile.id, profile.user_id, profile.organization_id)
    assert result == "ok"
    assert fake_dest.sent_payloads 