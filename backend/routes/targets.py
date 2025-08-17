from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db import models as m
from backend.schemas.targets import DestinationTargetCreate, DestinationTargetOut
from backend.deps import get_current_user, get_current_org_id

router = APIRouter(prefix="/targets", tags=["Targets"])

@router.get("/", response_model=List[DestinationTargetOut])
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_org_id: str = Depends(get_current_org_id),
) -> list[m.DestinationTarget]:
    res = await db.execute(
        select(m.DestinationTarget).where(m.DestinationTarget.organization_id == current_org_id)
    )
    return list(res.scalars().all())

@router.post("/", response_model=DestinationTargetOut, status_code=status.HTTP_201_CREATED)
async def create_target(
    payload: DestinationTargetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> m.DestinationTarget:
    obj = m.DestinationTarget(
        name=payload.name,
        display_name=payload.display_name,
        config=payload.config,
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj 