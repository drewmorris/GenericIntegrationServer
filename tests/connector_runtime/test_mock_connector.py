from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from connectors.onyx.connectors.mock_connector.connector import (
    MockConnector,
    MockConnectorCheckpoint,
)


class _MockTransport(httpx.MockTransport):
    def __init__(self) -> None:  # noqa: D401
        super().__init__(self._handler)

        # Build a single yield payload with one document and empty failures
        self._connector_payload = [
            {
                "documents": [
                    {
                        "id": "doc1",
                        "raw_text": "hello world",
                        "sections": [],
                        "source": "text",
                        "semantic_identifier": "doc1",
                        "metadata": {},
                    }
                ],
                "checkpoint": {"last_document_id": "doc1", "has_more": False},
                "failures": [],
            }
        ]

    def _handler(self, request: httpx.Request) -> httpx.Response:  # noqa: D401
        if request.url.path.endswith("get-documents"):
            return httpx.Response(200, json=self._connector_payload)
        if request.url.path.endswith("add-checkpoint"):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)


@pytest.fixture()
def mock_connector(monkeypatch: pytest.MonkeyPatch) -> MockConnector:  # noqa: D401
    transport = _MockTransport()
    client = httpx.Client(transport=transport)
    monkeypatch.setattr("httpx.Client", lambda *a, **kw: client)

    conn = MockConnector(mock_server_host="localhost", mock_server_port=9999)
    return conn


def test_mock_connector_iteration(mock_connector: MockConnector) -> None:  # noqa: D401
    # load credentials (triggers GET request)
    mock_connector.load_credentials({})

    cp = MockConnectorCheckpoint(last_document_id=None, has_more=False)

    docs = list(
        mock_connector.load_from_checkpoint(
            start=0, end=100, checkpoint=cp
        )
    )

    assert len(docs) == 1
    assert docs[0].model_dump().get("id") == "doc1" 