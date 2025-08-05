from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.factory import get_auth_provider
from backend.auth.db_provider import DbAuthProvider
from backend.db.session import get_db
from backend.auth.schemas import SignupRequest, LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from backend.auth.interfaces import TokenPair
from backend.settings import get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])


async def _provider(db: AsyncSession = Depends(get_db)):
    return get_auth_provider(db)


@router.post("/signup", response_model=TokenResponse)
async def signup(data: SignupRequest, provider: DbAuthProvider = Depends(_provider)):
    try:
        await provider.signup(data.email, data.password, data.organization)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    tokens: TokenPair = await provider.login(data.email, data.password)
    return TokenResponse(**tokens.__dict__)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, provider: DbAuthProvider = Depends(_provider)):
    try:
        tokens: TokenPair = await provider.login(data.email, data.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc
    return TokenResponse(**tokens.__dict__)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, provider: DbAuthProvider = Depends(_provider)):
    try:
        tokens: TokenPair = await provider.refresh(data.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(**tokens.__dict__)


@router.post("/logout", status_code=204)
async def logout(data: LogoutRequest, provider: DbAuthProvider = Depends(_provider)):
    await provider.revoke(data.refresh_token)
    return 