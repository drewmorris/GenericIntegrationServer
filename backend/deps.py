"""FastAPI dependencies for authentication and authorization."""

from fastapi import HTTPException, status, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from backend.settings import get_settings
from backend.db.session import get_db
from backend.db import models as m


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