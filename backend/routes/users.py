"""
User management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from backend.deps import get_current_user, get_db
from backend.db import models as m

router = APIRouter(prefix="/users", tags=["Users"])


class OrganizationOut(BaseModel):
    id: str
    name: str
    created_at: str
    billing_plan: str | None = None
    settings: dict | None = None

    class Config:
        from_attributes = True


class UserInfoOut(BaseModel):
    id: str
    email: str
    organization_id: str
    organization: OrganizationOut

    class Config:
        from_attributes = True


@router.get(
    "/me",
    response_model=UserInfoOut,
    summary="Get current user information",
    description="Retrieve detailed information about the currently authenticated user, "
                "including organization details and account settings."
)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> UserInfoOut:
    """Get current user info with organization details"""
    user_id = current_user["user_id"]
    
    # Fetch user with organization details
    query = (
        select(m.User)
        .where(m.User.id == user_id)
        .options(selectinload(m.User.organization))
    )
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfoOut(
        id=str(user.id),
        email=user.email,
        organization_id=str(user.organization_id),
        organization=OrganizationOut(
            id=str(user.organization.id),
            name=user.organization.name,
            created_at=user.organization.created_at.isoformat(),
            billing_plan=user.organization.billing_plan,
            settings=user.organization.settings,
        )
    )
