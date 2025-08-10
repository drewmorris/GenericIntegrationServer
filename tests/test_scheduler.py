import importlib
from types import SimpleNamespace

real_tasks = importlib.import_module("backend.orchestrator.tasks")
if not hasattr(real_tasks, "sync_dummy"):
    real_tasks.sync_dummy = SimpleNamespace(delay=lambda *a, **kw: None)  # type: ignore[attr-defined]

# Now safe to import scheduler
from datetime import datetime, timedelta

import pytest

from backend.orchestrator import scheduler as sched


class _FakeSession:
    def __init__(self, profiles):
        self._profiles = profiles
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, query):  # noqa: D401, ARG002
        class _Res:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                return self

            def all(self):
                return self._items

        return _Res(self._profiles)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_scan_due_profiles(monkeypatch):
    # Prepare a fake profile whose next_run_at is due
    now = datetime.utcnow()
    profile = SimpleNamespace(
        id="prof1",
        user_id="user1",
        organization_id="org1",
        interval_minutes=1,
        next_run_at=now - timedelta(minutes=5),
    )

    fake_sess = _FakeSession([profile])
    monkeypatch.setattr(sched, "SessionLocal", lambda: fake_sess)

    calls: list[list[str]] = []
    monkeypatch.setattr(getattr(sched, "sync_dummy"), "delay", lambda *a, **kw: calls.append(a))  # type: ignore[attr-defined]

    await sched.scan_due_profiles_async()

    # ensure task enqueued and profile next_run_at moved forward
    assert calls and calls[0][0] == "prof1"
    assert profile.next_run_at > now
    assert fake_sess.committed 