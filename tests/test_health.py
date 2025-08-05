from fastapi.testclient import TestClient

import importlib


def test_health() -> None:
    app = importlib.import_module("backend.main").app  # type: ignore[attr-defined]
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"} 