from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def set_current_org(session: AsyncSession, org_id: uuid.UUID) -> None:
    """Set PostgreSQL session variable used by RLS policies.

    Uses set_config(..., is_local := true) to scope to the current transaction,
    which is safe to parameterize under asyncpg.
    """
    await session.execute(
        text("SELECT set_config('app.current_org', :org, true)"),
        {"org": str(org_id)},
    ) 