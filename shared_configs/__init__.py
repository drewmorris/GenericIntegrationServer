"""Stubs for configuration helpers previously provided by Onyx EE code.

Only minimal functions used by the open-source connector runtime are included.
"""
__all__ = ["contextvars"]

from types import ModuleType
import contextvars as _cv

_context_tenant_id: _cv.ContextVar[str | None] = _cv.ContextVar("tenant_id", default=None)


class _ContextVars(ModuleType):
    def set_current_tenant_id(self, tenant_id: str | None) -> None:  # noqa: D401
        _context_tenant_id.set(tenant_id)

    def get_current_tenant_id(self) -> str | None:  # noqa: D401
        return _context_tenant_id.get()


import sys as _sys

module = _ContextVars("shared_configs.contextvars")
_sys.modules[__name__ + ".contextvars"] = module 