"""Thin stub package so vendored connectors can import `onyx.*` paths.
Only symbols referenced by the mocked connectors are provided.
"""
from __future__ import annotations

import sys
import types
from typing import Any

from pydantic import BaseModel


def _ensure(name: str) -> types.ModuleType:  # noqa: D401
    if name in sys.modules:
        return sys.modules[name]
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

# Create onyx.db.enums with IndexModelStatus enum
_db = _ensure("onyx.db")
_enums = _ensure("onyx.db.enums")
class IndexModelStatus(str):  # noqa: D401
    PENDING = "pending"
    COMPLETE = "complete"
    @classmethod
    def __get_pydantic_core_schema__(cls, *_):
        from pydantic_core import core_schema
        return core_schema.str_schema()
_enums.IndexModelStatus = IndexModelStatus  # type: ignore[attr-defined]

# onyx.access.models ExternalAccess stub
_access_pkg = _ensure("onyx.access")
_access_models = _ensure("onyx.access.models")

class ExternalAccess(BaseModel):  # noqa: D401
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

_access_models.ExternalAccess = ExternalAccess  # type: ignore[attr-defined]

# Map vendored connectors package so imports work
import importlib as _imp
sys.modules["onyx.connectors"] = _imp.import_module("connectors.onyx.connectors")

# configs.constants stub
_configs_pkg = _ensure("onyx.configs")
_configs_constants = _ensure("onyx.configs.constants")

class DocumentSource(str):  # noqa: D401
    INGESTION_API = "ingestion_api"

    @classmethod
    def __get_pydantic_core_schema__(cls, *_):  # noqa: D401
        from pydantic_core import core_schema
        return core_schema.str_schema()

_configs_constants.DocumentSource = DocumentSource  # type: ignore[attr-defined]
setattr(sys.modules[__name__], "DocumentSource", DocumentSource)
_configs_constants.INDEX_SEPARATOR = "::"  # type: ignore[attr-defined]
_configs_constants.PUBLIC_DOC_PAT = r"public"  # type: ignore[attr-defined]
_configs_constants.RETURN_SEPARATOR = "__RETURN__"  # type: ignore[attr-defined] 

# utils.text_processing stub
_utils = _ensure("onyx.utils")
_text_proc = _ensure("onyx.utils.text_processing")

def make_url_compatible(text: str) -> str:  # noqa: D401
    return text.replace(" ", "-")

_text_proc.make_url_compatible = make_url_compatible  # type: ignore[attr-defined] 

# indexing heartbeat stub
_indexing_pkg = _ensure("onyx.indexing")
_hb_mod = _ensure("onyx.indexing.indexing_heartbeat")
class IndexingHeartbeatInterface:  # noqa: D401
    async def heartbeat(self):
        return None
_hb_mod.IndexingHeartbeatInterface = IndexingHeartbeatInterface  # type: ignore[attr-defined] 

# utils.variable_functionality stub
_var_func = _ensure("onyx.utils.variable_functionality")

def fetch_ee_implementation_or_noop(*_a, **_kw):  # noqa: D401
    def _noop(*_args, **_kwargs):
        return None
    return _noop

_var_func.fetch_ee_implementation_or_noop = fetch_ee_implementation_or_noop  # type: ignore[attr-defined] 

# utils.logger stub
_logger_mod = _ensure("onyx.utils.logger")
import logging as _logging

def _setup_logger():  # noqa: D401
    return _logging.getLogger("onyx-stub")

_logger_mod.setup_logger = _setup_logger  # type: ignore[attr-defined] 