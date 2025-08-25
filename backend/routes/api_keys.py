from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.api_key import ApiKeyDescriptor
from backend.auth.schemas import UserRole
from backend.db.api_key import (
    fetch_api_keys,
    insert_api_key,
    update_api_key,
    regenerate_api_key,
    remove_api_key,
)
from backend.db.session import get_db
from backend.deps import get_current_user, get_current_org_id
from backend.db.models import User


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyRequest(BaseModel):
    name: str | None = None
    role: UserRole = UserRole.BASIC


class ApiKeyUpdateRequest(BaseModel):
    name: str | None = None
    role: UserRole | None = None


@router.get(
    "/", 
    response_model=list[ApiKeyDescriptor],
    summary="List API keys",
    description="Retrieve all API keys for the current organization. "
                "API keys provide programmatic access to the Integration Server API "
                "and can be assigned different roles (BASIC, ADMIN) for access control."
)
def list_api_keys(
    current_user: User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """List all API keys for the current organization."""
    # For now, return all keys (would filter by org in multi-tenant)
    return fetch_api_keys(db)


@router.post(
    "/", 
    response_model=ApiKeyDescriptor,
    summary="Create API key",
    description="Create a new API key for programmatic access. "
                "Specify a name for identification and role for access control. "
                "The API key value is returned only once - store it securely."
)
def create_api_key(
    request: ApiKeyRequest,
    current_user: User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Create a new API key."""
    api_key_args = {
        "name": request.name,
        "role": request.role.value,
        "organization_id": current_user.organization_id,
    }
    return insert_api_key(db, api_key_args, current_user.id)


@router.put("/{api_key_id}", response_model=ApiKeyDescriptor)
def update_existing_api_key(
    api_key_id: int,
    request: ApiKeyUpdateRequest,
    current_user: User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Update an existing API key."""
    api_key_args = {}
    if request.name is not None:
        api_key_args["name"] = request.name
    if request.role is not None:
        api_key_args["role"] = request.role.value
    
    return update_api_key(db, api_key_id, api_key_args)


@router.post("/{api_key_id}/regenerate", response_model=ApiKeyDescriptor)
def regenerate_existing_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Regenerate an existing API key."""
    return regenerate_api_key(db, api_key_id)


@router.delete("/{api_key_id}")
def delete_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Delete an API key."""
    remove_api_key(db, api_key_id)
    return {"message": "API key deleted successfully"}
