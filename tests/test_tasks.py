import uuid
import pytest
from types import SimpleNamespace

from backend.orchestrator import tasks as task_mod


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, query):  # noqa: D401, ARG002
        class _Result:
            def scalar_one(self_non):
                # Return a fake connector profile
                return SimpleNamespace(
                    id=profile_id,
                    name="Prof",
                    source="mock_source",
                    connector_config={"destination": "dummy", "dummy": {}},
                )
        return _Result()


class _DummyDest:
    async def send(self, *, payload, profile_config):  # noqa: D401, ARG002
        self.payload = list(payload)
        self.profile_config = profile_config


async def _fake_run_with_syncrow(profile_id, org_id, user_id, runner):  # noqa: D401, ARG001
    # Execute runner with fake session
    await runner(_FakeSession())


profile_id = str(uuid.uuid4())


def test_sync_connector(monkeypatch):
    monkeypatch.setattr(task_mod, "AsyncSessionLocal", lambda: _FakeSession())
    async def _dummy_set_current_org(*a, **kw):
        return None
    monkeypatch.setattr(task_mod, "set_current_org", _dummy_set_current_org)
    monkeypatch.setattr(task_mod, "run_with_syncrow", _fake_run_with_syncrow)
    monkeypatch.setattr(task_mod, "get_destination", lambda name: _DummyDest)

    res = task_mod.sync_connector(profile_id, str(uuid.uuid4()), str(uuid.uuid4()))
    assert res == "ok" 