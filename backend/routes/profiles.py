from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import models as m
from backend.db.session import get_db
from backend.schemas.profiles import (
    ConnectorProfileCreate,
    ConnectorProfileOut,
    ConnectorProfileUpdate,
)

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get(
    "/",
    response_model=List[ConnectorProfileOut],
    summary="List connector profiles",
    description="Return all connector profiles visible in the current organization context.",
)
async def list_profiles(db: AsyncSession = Depends(get_db)) -> list[m.ConnectorProfile]:
    res = await db.execute(select(m.ConnectorProfile))
    return res.scalars().all()


@router.post(
    "/",
    response_model=ConnectorProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create connector profile",
    description="Create a new connector profile (source + destination config). The calling user/org IDs must be supplied in the payload for now; in the future they will be inferred from auth context.",
)
async def create_profile(payload: ConnectorProfileCreate, db: AsyncSession = Depends(get_db)) -> m.ConnectorProfile:
    obj = m.ConnectorProfile(
        id=uuid.uuid4(),
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        name=payload.name,
        source=payload.source,
        connector_config=payload.connector_config,
        interval_minutes=payload.interval_minutes,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get(
    "/{profile_id}",
    response_model=ConnectorProfileOut,
    summary="Get connector profile",
    description="Retrieve a single connector profile by ID.",
)
async def get_profile(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> m.ConnectorProfile:
    obj = await db.get(m.ConnectorProfile, profile_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return obj


@router.patch(
    "/{profile_id}",
    response_model=ConnectorProfileOut,
    summary="Update connector profile",
    description="Partial update of connector profile settings (name, interval, connector_config).",
)
async def update_profile(
    profile_id: uuid.UUID,
    payload: ConnectorProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> m.ConnectorProfile:
    obj = await db.get(m.ConnectorProfile, profile_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj 