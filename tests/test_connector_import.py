import pytest


try:
    from connectors.onyx.connectors.interfaces import BaseConnector

    class DummyConnector(BaseConnector):
        def load_credentials(self, credentials):
            return None

    HAVE_RUNTIME = True
except ImportError:
    HAVE_RUNTIME = False


@pytest.mark.skipif(not HAVE_RUNTIME, reason="Connector runtime dependencies missing")
def test_connector_runtime_import() -> None:
    connector = DummyConnector()  # type: ignore[name-defined]
    assert isinstance(connector, BaseConnector)  # type: ignore[name-defined] 