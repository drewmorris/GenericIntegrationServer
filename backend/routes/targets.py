from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db import models as m
from backend.schemas.targets import DestinationTargetCreate, DestinationTargetOut

router = APIRouter(prefix="/targets", tags=["Targets"])

@router.get("/", response_model=List[DestinationTargetOut])
async def list_targets(db: AsyncSession = Depends(get_db)) -> list[m.DestinationTarget]:
    res = await db.execute(select(m.DestinationTarget))
    return list(res.scalars().all())

@router.post("/", response_model=DestinationTargetOut, status_code=status.HTTP_201_CREATED)
async def create_target(payload: DestinationTargetCreate, db: AsyncSession = Depends(get_db)) -> m.DestinationTarget:
    obj = m.DestinationTarget(
        name=payload.name,
        display_name=payload.display_name,
        config=payload.config,
        organization_id=payload.organization_id,
        user_id=payload.user_id,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj 