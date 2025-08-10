"""Test fixtures and stub modules for vendored Onyx connector runtime."""
from __future__ import annotations

import sys
import types
from typing import Any, Iterable, Iterator, TypeVar, Generic

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Minimal stubs so `connectors/onyx` runtime can import without full Onyx repo
# ---------------------------------------------------------------------------

def _ensure(mod_name: str) -> types.ModuleType:  # noqa: D401
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    module = types.ModuleType(mod_name)
    sys.modules[mod_name] = module
    return module

# Root packages
_ensure("onyx")
_ensure("onyx.access")
_ensure("onyx.connectors")
_ensure("onyx.connectors.interfaces")
_ensure("onyx.connectors.models")
_ensure("onyx.utils")

# onyx.utils.logger.setup_logger
logger_mod = _ensure("onyx.utils.logger")

def setup_logger() -> Any:  # noqa: D401
    import logging
    return logging.getLogger("onyx-stub")

logger_mod.setup_logger = setup_logger  # type: ignore[attr-defined]

# ------------------------------------------------------------------
# Connector interface & model stubs (only attrs used by MockConnector)
# ------------------------------------------------------------------
interfaces_mod = sys.modules["onyx.connectors.interfaces"]

T = TypeVar("T")
class CheckpointedConnectorWithPermSync(Generic[T]):
    pass

class SecondsSinceUnixEpoch(int):  # noqa: D401
    pass

interfaces_mod.CheckpointedConnectorWithPermSync = CheckpointedConnectorWithPermSync  # type: ignore[attr-defined]
interfaces_mod.SecondsSinceUnixEpoch = SecondsSinceUnixEpoch  # type: ignore[attr-defined]
interfaces_mod.CheckpointOutput = Iterable  # simple alias

models_mod = sys.modules["onyx.connectors.models"]

class ConnectorCheckpoint(BaseModel):  # noqa: D401
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
class ConnectorFailure(BaseModel):  # noqa: D401
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
class Document(BaseModel):  # noqa: D401
    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow",
    }
    id: str | None = None
    raw_text: str | None = None
models_mod.ConnectorCheckpoint = ConnectorCheckpoint  # type: ignore[attr-defined]
models_mod.ConnectorFailure = ConnectorFailure  # type: ignore[attr-defined]
models_mod.Document = Document  # type: ignore[attr-defined]

# access models
access_mod = _ensure("onyx.access.models")
class ExternalAccess:  # noqa: D401
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)
access_mod.ExternalAccess = ExternalAccess  # type: ignore[attr-defined]

# onyx.db.enums
db_mod = _ensure("onyx.db")
enums_mod = _ensure("onyx.db.enums")

class IndexModelStatus(str):  # noqa: D401
    PENDING = "pending"
    COMPLETE = "complete"

enums_mod.IndexModelStatus = IndexModelStatus  # type: ignore[attr-defined] 