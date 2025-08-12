from __future__ import annotations

import uuid

try:
    from shared_configs.contextvars import set_current_tenant_id  # type: ignore
except Exception:  # noqa: BLE001
    def set_current_tenant_id(_: str) -> None:  # type: ignore
        pass


def set_legacy_tenant(org_id: uuid.UUID) -> None:
    set_current_tenant_id(str(org_id)) 