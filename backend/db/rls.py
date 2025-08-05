from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def set_current_org(session: AsyncSession, org_id: uuid.UUID) -> None:
    """Set PostgreSQL session variable used by RLS policies.

    Should be executed once per connection checkout.
    """
    await session.execute(text("SET LOCAL app.current_org = :org"), {"org": str(org_id)}) 