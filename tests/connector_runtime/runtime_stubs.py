"""Stub modules so vendored Onyx runtime can import without full upstream code.
Imported by tests; registers modules in sys.modules at import time."""
from __future__ import annotations
import sys, types
from typing import Any, Iterable, TypeVar, Generic
from pydantic import BaseModel

def _ensure(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

# root packages
for pkg in ["onyx", "onyx.access", "onyx.connectors", "onyx.connectors.interfaces", "onyx.connectors.models", "onyx.utils"]:
    _ensure(pkg)

# logger stub
a_logger = _ensure("onyx.utils.logger")
import logging

a_logger.setup_logger = lambda: logging.getLogger("onyx-stub")  # type: ignore[attr-defined]

# interfaces stubs
interfaces_mod = sys.modules["onyx.connectors.interfaces"]
T = TypeVar("T")
class CheckpointedConnectorWithPermSync(Generic[T]):
    pass
class SecondsSinceUnixEpoch(int):
    pass
interfaces_mod.CheckpointedConnectorWithPermSync = CheckpointedConnectorWithPermSync  # type: ignore[attr-defined]
interfaces_mod.SecondsSinceUnixEpoch = SecondsSinceUnixEpoch  # type: ignore[attr-defined]
interfaces_mod.CheckpointOutput = Iterable  # type: ignore[attr-defined]

# models stub
models_mod = sys.modules["onyx.connectors.models"]
class ConnectorCheckpoint(BaseModel):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
class ConnectorFailure(BaseModel):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
class Document(BaseModel):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
    id: str | None = None
    raw_text: str | None = None
models_mod.ConnectorCheckpoint = ConnectorCheckpoint  # type: ignore[attr-defined]
models_mod.ConnectorFailure = ConnectorFailure  # type: ignore[attr-defined]
models_mod.Document = Document  # type: ignore[attr-defined]

# access models
access_mod = _ensure("onyx.access.models")
class ExternalAccess(BaseModel):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
access_mod.ExternalAccess = ExternalAccess  # type: ignore[attr-defined]

# db.enums
_enums = _ensure("onyx.db.enums")
class IndexModelStatus(str):
    PENDING = "pending"
    COMPLETE = "complete"
_enums.IndexModelStatus = IndexModelStatus  # type: ignore[attr-defined] 