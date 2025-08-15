from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import models as m
from backend.db.session import get_db
from backend.schemas.profiles import (
    ConnectorProfileCreate,
    ConnectorProfileOut,
    ConnectorProfileUpdate,
)
from backend.orchestrator.tasks import sync_connector

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get(
    "/",
    response_model=List[ConnectorProfileOut],
    summary="List connector profiles",
    description="Return all connector profiles visible in the current organization context.",
)
async def list_profiles(db: AsyncSession = Depends(get_db)) -> list[m.ConnectorProfile]:
    res = await db.execute(select(m.ConnectorProfile))
    return list(res.scalars().all())

# Support no-trailing-slash variant to prevent 307 redirects under proxies
@router.get(
    "",
    response_model=List[ConnectorProfileOut],
    include_in_schema=False,
)
async def list_profiles_no_slash(db: AsyncSession = Depends(get_db)) -> list[m.ConnectorProfile]:
    return await list_profiles(db)


@router.post(
    "/",
    response_model=ConnectorProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create connector profile",
    description="Create a new connector profile (source + destination config). The calling user/org IDs must be supplied in the payload for now; in the future they will be inferred from auth context.",
)
async def create_profile(payload: ConnectorProfileCreate, db: AsyncSession = Depends(get_db)) -> ConnectorProfileOut:
    obj = m.ConnectorProfile(
        id=uuid.uuid4(),
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        name=payload.name,
        source=payload.source,
        connector_config=payload.connector_config,
        interval_minutes=payload.interval_minutes,
        credential_id=payload.credential_id,
        status=payload.status,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ConnectorProfileOut.from_orm(obj)

@router.post(
    "",
    response_model=ConnectorProfileOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_profile_no_slash(payload: ConnectorProfileCreate, db: AsyncSession = Depends(get_db)) -> ConnectorProfileOut:
    return await create_profile(payload, db)


@router.get(
    "/{profile_id}",
    response_model=ConnectorProfileOut,
    summary="Get connector profile",
    description="Retrieve a single connector profile by ID.",
)
async def get_profile(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ConnectorProfileOut:
    obj = await db.get(m.ConnectorProfile, profile_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ConnectorProfileOut.from_orm(obj)


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
) -> ConnectorProfileOut:
    obj = await db.get(m.ConnectorProfile, profile_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return ConnectorProfileOut.from_orm(obj)


@router.post(
    "/{profile_id}/run",
    status_code=status.HTTP_200_OK,
    summary="Trigger sync run",
    description="Manually trigger a sync run for the specified connector profile.",
)
async def trigger_profile_sync(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Trigger an immediate sync run for a connector profile."""
    # Verify profile exists
    obj = await db.get(m.ConnectorProfile, profile_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    # Trigger the sync via Celery
    task = sync_connector.delay(str(profile_id), str(obj.organization_id), str(obj.user_id))
    
    return {"message": "Sync triggered", "task_id": task.id, "profile_id": str(profile_id)}


@router.get(
    "/{profile_id}/runs",
    summary="List sync runs for profile",
    description="Return historical sync run rows for the given connector profile.",
)
async def list_profile_runs(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List sync runs for a specific profile."""
    # Verify profile exists
    obj = await db.get(m.ConnectorProfile, profile_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    # Get sync runs for this profile
    result = await db.execute(
        select(m.SyncRun).where(m.SyncRun.profile_id == profile_id).order_by(m.SyncRun.started_at.desc())
    )
    runs = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "profile_id": str(r.profile_id),
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "records_synced": r.records_synced,
            "created_at": r.started_at.isoformat() if r.started_at else None,
        }
        for r in runs
    ] 