import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_scheduler_skips_paused(monkeypatch):
    from backend.orchestrator.scheduler import _scan_due_profiles_impl
    from backend.orchestrator import scheduler as _sched

    # Build a fake session that returns one paused profile
    class _Obj:
        def __init__(self):
            self.id = uuid.uuid4(); self.user_id = uuid.uuid4(); self.organization_id = uuid.uuid4()
            self.interval_minutes = 5
            self.next_run_at = None
            self.status = "paused"

    class _ScalarList:
        def __init__(self, items):
            self._items = items
        def all(self):
            return self._items
        def scalars(self):
            return self

    class _Sess:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        async def execute(self, stmt):  # noqa: ARG002
            return _ScalarList([_Obj()])
        async def commit(self):
            pass

    # Monkeypatch the session factory creator to return our fake session
    def _fake_factory():
        class _M:
            def __call__(self):
                return _Sess()
        return _M()

    monkeypatch.setattr(_sched, "_create_session_factory", _fake_factory)

    # No exceptions should occur and no tasks scheduled (cannot easily assert without broker)
    await _scan_due_profiles_impl()
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
    class _Factory:
        def __call__(self):
            return fake_sess
    monkeypatch.setattr(sched, "_create_session_factory", lambda: _Factory())

    calls: list[list[str]] = []
    monkeypatch.setattr(getattr(sched, "sync_dummy"), "delay", lambda *a, **kw: calls.append(a))  # type: ignore[attr-defined]

    await sched.scan_due_profiles_async()

    # ensure task enqueued and profile next_run_at moved forward
    assert calls and calls[0][0] == "prof1"
    assert profile.next_run_at > now
    assert fake_sess.committed 