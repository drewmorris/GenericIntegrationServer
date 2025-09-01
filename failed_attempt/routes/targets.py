from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db import models as m
from backend.schemas.targets import DestinationTargetCreate, DestinationTargetOut, DestinationTargetUpdate
from backend.deps import get_current_user, get_current_org_id

router = APIRouter(prefix="/targets", tags=["Targets"])

@router.get(
    "/", 
    response_model=List[DestinationTargetOut],
    summary="List destination targets",
    description="Retrieve all destination targets configured for the current organization. "
                "Destination targets are specific instances of destinations (like CleverBrag, Onyx) "
                "with their connection details and configuration."
)
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_org_id: str = Depends(get_current_org_id),
) -> list[m.DestinationTarget]:
    res = await db.execute(
        select(m.DestinationTarget).where(m.DestinationTarget.organization_id == current_org_id)
    )
    return list(res.scalars().all())

@router.post(
    "/", 
    response_model=DestinationTargetOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Create destination target",
    description="Create a new destination target instance with specific configuration. "
                "This defines where synchronized documents will be sent (e.g., CleverBrag API endpoint). "
                "Each target includes connection details, credentials, and destination-specific settings.",
)
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

@router.put(
    "/{target_id}",
    response_model=DestinationTargetOut,
    summary="Update destination target",
    description="Update an existing destination target's configuration or display name. "
                "Only the fields provided in the request body will be updated.",
)
async def update_target(
    target_id: str,
    payload: DestinationTargetUpdate,
    db: AsyncSession = Depends(get_db),
    current_org_id: str = Depends(get_current_org_id),
) -> m.DestinationTarget:
    # Find the target and verify ownership
    res = await db.execute(
        select(m.DestinationTarget).where(
            m.DestinationTarget.id == target_id,
            m.DestinationTarget.organization_id == current_org_id
        )
    )
    target = res.scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination target not found"
        )
    
    # Update fields
    if payload.display_name is not None:
        target.display_name = payload.display_name
    if payload.config is not None:
        target.config = payload.config
    
    await db.commit()
    await db.refresh(target)
    return target

@router.delete(
    "/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete destination target",
    description="Delete a destination target. This will also remove any associated connector-credential pairs "
                "and stop any active syncs to this destination.",
)
async def delete_target(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_org_id: str = Depends(get_current_org_id),
):
    # Find the target and verify ownership
    res = await db.execute(
        select(m.DestinationTarget).where(
            m.DestinationTarget.id == target_id,
            m.DestinationTarget.organization_id == current_org_id
        )
    )
    target = res.scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination target not found"
        )
    
    # Delete the target (cascading deletes will handle related objects)
    await db.delete(target)
    await db.commit() 