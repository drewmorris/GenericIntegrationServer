import pytest

from backend.orchestrator.tasks import sync_connector

def test_celery_retry_settings() -> None:  # noqa: D401
    assert sync_connector.max_retries == 5  # type: ignore[attr-defined]
    assert sync_connector.retry_backoff is True  # type: ignore[attr-defined] 