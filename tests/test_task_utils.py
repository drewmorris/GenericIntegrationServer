import uuid
import pytest
from types import SimpleNamespace

from backend.orchestrator import task_utils as tu


class _FakeSession:
    def __init__(self):
        self.add_calls = 0
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def commit(self):
        self.commit_calls += 1

    async def execute(self, query):  # noqa: D401, ARG002
        return SimpleNamespace()  # query result ignored

    def add(self, obj):  # noqa: D401, ARG002
        self.add_calls += 1


@pytest.mark.asyncio
async def test_run_with_syncrow_success(monkeypatch):
    fake_sess = _FakeSession()
    monkeypatch.setattr(tu, "AsyncSessionLocal", lambda: fake_sess)
    async def _dummy_set_current_org(*a, **kw):
        return None
    monkeypatch.setattr(tu, "set_current_org", _dummy_set_current_org)

    async def runner(sess):  # noqa: D401
        assert sess is fake_sess
        return 5

    await tu.run_with_syncrow(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), runner)

    # one add during creation
    assert fake_sess.add_calls == 1
    # commit called at least twice (create + finish)
    assert fake_sess.commit_calls >= 2


@pytest.mark.asyncio
async def test_run_with_syncrow_failure(monkeypatch):
    fake_sess = _FakeSession()
    monkeypatch.setattr(tu, "AsyncSessionLocal", lambda: fake_sess)
    async def _dummy_set_current_org(*a, **kw):
        return None
    monkeypatch.setattr(tu, "set_current_org", _dummy_set_current_org)

    async def runner(sess):  # noqa: D401
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await tu.run_with_syncrow(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), runner)

    # failure still commits finish step
    assert fake_sess.commit_calls >= 2 