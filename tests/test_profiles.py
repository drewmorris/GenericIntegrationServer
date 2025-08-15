import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes import profiles as profiles_router


class _FakeSession:
    def __init__(self):
        self.objs: dict[str, SimpleNamespace] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, stmt):  # noqa: D401, ARG002
        class _Res:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                return self

            def all(self):
                return list(self._items)

        return _Res(self.objs.values())

    async def get(self, model, obj_id):  # noqa: D401, ARG002
        return self.objs.get(str(obj_id))

    def add(self, obj):  # noqa: D401, ARG002
        self.objs[str(obj.id)] = obj

        # ensure obj has created_at for schema
        if not hasattr(obj, "created_at"):
            obj.created_at = None

    async def commit(self):
        pass

    async def refresh(self, obj):  # noqa: D401, ARG002
        pass


@pytest.fixture()
def client(monkeypatch):
    fake_db = _FakeSession()

    async def _override_get_db():  # noqa: D401
        async with fake_db as sess:
            yield sess

    app.dependency_overrides[profiles_router.get_db] = _override_get_db  # type: ignore[arg-type]
    with TestClient(app) as c:
        yield c, fake_db
    app.dependency_overrides.clear()


def _sample_payload(org_id, user_id):
    return {
        "organization_id": str(org_id),
        "user_id": str(user_id),
        "name": "Test Prof",
        "source": "mock_source",
        "connector_config": {"k": "v"},
        "interval_minutes": 5,
        "credential_id": None,
        "status": "active",
    }


def test_profile_crud(client):
    c, db = client
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # create
    resp = c.post("/profiles/", json=_sample_payload(org_id, user_id), headers={"X-Org-ID": str(org_id)})
    assert resp.status_code == 201
    prof_id = resp.json()["id"]

    # list
    resp = c.get("/profiles/", headers={"X-Org-ID": str(org_id)})
    assert resp.status_code == 200 and len(resp.json()) == 1

    # get
    resp = c.get(f"/profiles/{prof_id}", headers={"X-Org-ID": str(org_id)})
    assert resp.status_code == 200 and resp.json()["id"] == prof_id

    # patch
    resp = c.patch(f"/profiles/{prof_id}", json={"interval_minutes": 30}, headers={"X-Org-ID": str(org_id)})
    assert resp.status_code == 200 and resp.json()["interval_minutes"] == 30 