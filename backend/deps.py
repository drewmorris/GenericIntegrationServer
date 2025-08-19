"""FastAPI dependencies for authentication and authorization."""

from fastapi import HTTPException, status, Header, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from backend.settings import get_settings
from backend.db.session import get_db
from backend.db import models as m
from backend.auth.api_key import get_hashed_api_key_from_request
from backend.db.api_key import fetch_user_for_api_key


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract current user from JWT token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ", 1)[1]
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = (await db.execute(select(m.User).where(m.User.email == email))).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "email": user.email,
    }


async def get_current_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """Extract just the user ID from current user."""
    return current_user["user_id"]


async def get_current_org_id(current_user: dict = Depends(get_current_user)) -> str:
    """Extract just the organization ID from current user."""
    return current_user["organization_id"]


async def get_current_user_or_api_key(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user from either JWT token or API key."""
    # First try API key authentication
    hashed_api_key = get_hashed_api_key_from_request(request)
    if hashed_api_key:
        api_user = await fetch_user_for_api_key(hashed_api_key, db)
        if api_user:
            return {
                "user_id": str(api_user.id),
                "organization_id": str(api_user.organization_id),
                "email": api_user.email,
            }
    
    # Fall back to JWT authentication
    return await get_current_user(authorization, db)