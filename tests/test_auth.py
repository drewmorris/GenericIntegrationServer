from fastapi.testclient import TestClient

import importlib

main_mod = importlib.import_module("backend.main")
app = main_mod.app  # type: ignore[attr-defined]

auth_routes = importlib.import_module("backend.routes.auth")

# Create a singleton in-memory provider to persist users across requests
from backend.auth.db_provider import DbAuthProvider  # type: ignore
from backend.auth.factory import get_auth_provider

singleton_provider = DbAuthProvider(db=None)  # type: ignore[arg-type]


async def override_provider():
    return singleton_provider

app.dependency_overrides[auth_routes._provider] = override_provider

# also override get_auth_provider globally to ensure other code paths use the singleton
auth_routes.get_auth_provider = lambda db=None: singleton_provider  # type: ignore

auth_client = TestClient(app)


def test_signup_and_login() -> None:
    signup_resp = auth_client.post(
        "/auth/signup",
        json={"email": "user@example.com", "password": "strongpassword", "organization": "TestOrg"},
    )
    assert signup_resp.status_code == 200
    token_data = signup_resp.json()
    assert "access_token" in token_data and "refresh_token" in token_data

    login_resp = auth_client.post(
        "/auth/login", json={"email": "user@example.com", "password": "strongpassword"}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["access_token"] != ""

    refresh_resp = auth_client.post("/auth/refresh", json={"refresh_token": token_data["refresh_token"]})
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json() 