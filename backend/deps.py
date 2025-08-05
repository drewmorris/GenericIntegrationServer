from __future__ import annotations

import uuid

from fastapi import Header, HTTPException, status


def get_org_id(x_org_id: str | None = Header(default=None, alias="X-Org-ID")) -> uuid.UUID:
    """Extract organization ID from request header."""
    if x_org_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Org-ID header missing")
    try:
        return uuid.UUID(x_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Org-ID header") from exc 