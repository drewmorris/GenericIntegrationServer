"""
Custom OAuth handling for Google services (Gmail, Google Drive)
Since these connectors don't inherit from OAuthConnector, they need special handling.
"""
from __future__ import annotations

import os
import uuid
import json
import base64
from datetime import datetime
from urllib.parse import urlencode

import redis
from fastapi import APIRouter, HTTPException, Query, Request, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_db
from backend.db import models as m
from backend.security.crypto import encrypt_dict
# JWT authentication function (avoiding circular imports)
async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract current user from JWT token (for OAuth flows)."""
    from backend.settings import get_settings
    from jose import jwt
    from sqlalchemy import select
    
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    
    token = authorization.split(" ", 1)[1]
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Token missing subject")
    
    user = (await db.execute(select(m.User).where(m.User.email == email))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "email": email,
    }

router = APIRouter(prefix="/oauth/google", tags=["Google OAuth"])

# Google OAuth configuration
GOOGLE_OAUTH_CLIENT_ID = os.getenv("OAUTH_GOOGLE_DRIVE_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("OAUTH_GOOGLE_DRIVE_CLIENT_SECRET", "")

# Redis configuration for OAuth state management
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def get_redis_client() -> redis.Redis:
    """Get Redis client for OAuth state management."""
    return redis.from_url(REDIS_URL, decode_responses=True)

# Gmail scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
]

# Google Drive scopes  
GOOGLE_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly", 
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
]


@router.get("/gmail/start")
async def gmail_oauth_start(
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start OAuth flow for Gmail connector (legacy pattern)."""
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=400, 
            detail="Google OAuth not configured. Please set OAUTH_GOOGLE_DRIVE_CLIENT_ID and OAUTH_GOOGLE_DRIVE_CLIENT_SECRET"
        )
    
    # Generate OAuth state UUID (legacy pattern)
    oauth_uuid = uuid.uuid4()
    oauth_uuid_str = str(oauth_uuid)
    
    # Create OAuth session data to store in Redis
    session_data = {
        "user_id": user["user_id"],
        "organization_id": user["organization_id"],
        "email": user.get("email", ""),
        "connector": "gmail",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Store session in Redis with UUID key (legacy pattern)
    r = get_redis_client()
    r_key = f"da_oauth:{oauth_uuid_str}"
    r.setex(r_key, 600, json.dumps(session_data))  # 10 minute expiry
    
    # Encode UUID as base64 for state parameter (legacy pattern)
    uuid_bytes = oauth_uuid.bytes
    padded_state = base64.urlsafe_b64encode(uuid_bytes).decode('utf-8').rstrip('=')
    
    # Build redirect URI - redirect to backend (legacy pattern)
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url}/oauth/google/gmail/callback"
    
    # Build OAuth URL
    oauth_params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": " ".join(GMAIL_SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": padded_state,
        "include_granted_scopes": "true",
    }
    
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(oauth_params)}"
    
    return {"authorization_url": authorization_url}


@router.get("/drive/start") 
async def google_drive_oauth_start(
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start OAuth flow for Google Drive connector (legacy pattern)."""
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth not configured. Please set OAUTH_GOOGLE_DRIVE_CLIENT_ID and OAUTH_GOOGLE_DRIVE_CLIENT_SECRET"
        )
    
    # Generate OAuth state UUID (legacy pattern)
    oauth_uuid = uuid.uuid4()
    oauth_uuid_str = str(oauth_uuid)
    
    # Create OAuth session data to store in Redis
    session_data = {
        "user_id": user["user_id"],
        "organization_id": user["organization_id"],
        "email": user.get("email", ""),
        "connector": "google_drive",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Store session in Redis with UUID key (legacy pattern)
    r = get_redis_client()
    r_key = f"da_oauth:{oauth_uuid_str}"
    r.setex(r_key, 600, json.dumps(session_data))  # 10 minute expiry
    
    # Encode UUID as base64 for state parameter (legacy pattern)
    uuid_bytes = oauth_uuid.bytes
    padded_state = base64.urlsafe_b64encode(uuid_bytes).decode('utf-8').rstrip('=')
    
    # Build redirect URI - redirect to backend (legacy pattern)
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url}/oauth/google/drive/callback"
    
    # Build OAuth URL
    oauth_params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": " ".join(GOOGLE_DRIVE_SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent", 
        "state": padded_state,
        "include_granted_scopes": "true",
    }
    
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(oauth_params)}"
    
    return {"authorization_url": authorization_url}


@router.get("/gmail/callback")
async def gmail_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Gmail OAuth callback (legacy pattern)."""
    import httpx
    from fastapi.responses import RedirectResponse
    
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")
    
    try:
        # Recover the state UUID (legacy pattern)
        padded_state = state + "=" * (-len(state) % 4)  # Add padding back
        uuid_bytes = base64.urlsafe_b64decode(padded_state)
        oauth_uuid = uuid.UUID(bytes=uuid_bytes)
        oauth_uuid_str = str(oauth_uuid)
        
        # Retrieve session from Redis (legacy pattern)
        r = get_redis_client()
        r_key = f"da_oauth:{oauth_uuid_str}"
        session_json = r.get(r_key)
        
        if not session_json:
            raise HTTPException(
                status_code=400,
                detail=f"Gmail OAuth failed - OAuth state key not found: key={r_key}"
            )
        
        session_data = json.loads(session_json)
        
        # Build redirect URI (must match what was sent to Google)  
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        redirect_uri = f"{base_url}/oauth/google/gmail/callback"
        
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Token exchange failed: {token_response.text}"
                )
            
            tokens = token_response.json()
            
            # Create credential data in legacy format
            authorized_user_info = {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "refresh_token": tokens.get("refresh_token"),
                "type": "authorized_user"
            }
            
            # Create credential dict in legacy format
            credential_dict = {
                "google_tokens": json.dumps(authorized_user_info),
                "google_primary_admin": session_data["email"],
                "authentication_method": "oauth_interactive"
            }
            
            # Save credential to database (legacy pattern)
            credential = m.Credential(
                id=uuid.uuid4(),
                organization_id=uuid.UUID(session_data["organization_id"]),
                user_id=uuid.UUID(session_data["user_id"]),
                connector_name="gmail",
                provider_key="oauth",
                credential_json=encrypt_dict(credential_dict),
                expires_at=None,
                status="active",
                encryption_key_version=1,
                created_by_ip=request.client.host if request.client else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(credential)
            await db.commit()
            await db.refresh(credential)
            
            # Clean up Redis session
            r.delete(r_key)
            
            # Redirect to frontend with success (legacy pattern)
            frontend_url = f"http://localhost:5173/connectors?credential_id={credential.id}&connector=gmail&success=true"
            return RedirectResponse(url=frontend_url, status_code=302)
            
    except Exception as e:
        # Redirect to frontend with error (legacy pattern)
        frontend_url = f"http://localhost:5173/connectors?error=oauth_failed&message={str(e)}"
        return RedirectResponse(url=frontend_url, status_code=302)


@router.get("/drive/callback")
async def google_drive_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google Drive OAuth callback (legacy pattern)."""
    import httpx
    from fastapi.responses import RedirectResponse
    
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")
    
    try:
        # Recover the state UUID (legacy pattern)
        padded_state = state + "=" * (-len(state) % 4)  # Add padding back
        uuid_bytes = base64.urlsafe_b64decode(padded_state)
        oauth_uuid = uuid.UUID(bytes=uuid_bytes)
        oauth_uuid_str = str(oauth_uuid)
        
        # Retrieve session from Redis (legacy pattern)
        r = get_redis_client()
        r_key = f"da_oauth:{oauth_uuid_str}"
        session_json = r.get(r_key)
        
        if not session_json:
            raise HTTPException(
                status_code=400,
                detail=f"Google Drive OAuth failed - OAuth state key not found: key={r_key}"
            )
        
        session_data = json.loads(session_json)
        
        # Build redirect URI (must match what was sent to Google)
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        redirect_uri = f"{base_url}/oauth/google/drive/callback"
        
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Token exchange failed: {token_response.text}"
                )
            
            tokens = token_response.json()
            
            # Create credential data in legacy format
            authorized_user_info = {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "refresh_token": tokens.get("refresh_token"),
                "type": "authorized_user"
            }
            
            # Create credential dict in legacy format
            credential_dict = {
                "google_tokens": json.dumps(authorized_user_info),
                "google_primary_admin": session_data["email"],
                "authentication_method": "oauth_interactive"
            }
            
            # Save credential to database (legacy pattern)
            credential = m.Credential(
                id=uuid.uuid4(),
                organization_id=uuid.UUID(session_data["organization_id"]),
                user_id=uuid.UUID(session_data["user_id"]),
                connector_name="google_drive",
                provider_key="oauth",
                credential_json=encrypt_dict(credential_dict),
                expires_at=None,
                status="active",
                encryption_key_version=1,
                created_by_ip=request.client.host if request.client else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(credential)
            await db.commit()
            await db.refresh(credential)
            
            # Clean up Redis session
            r.delete(r_key)
            
            # Redirect to frontend with success (legacy pattern)
            frontend_url = f"http://localhost:5173/connectors?credential_id={credential.id}&connector=google_drive&success=true"
            return RedirectResponse(url=frontend_url, status_code=302)
            
    except Exception as e:
        # Redirect to frontend with error (legacy pattern)
        frontend_url = f"http://localhost:5173/connectors?error=oauth_failed&message={str(e)}"
        return RedirectResponse(url=frontend_url, status_code=302)
