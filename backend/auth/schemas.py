import uuid
from enum import Enum
from pydantic import BaseModel


class UserRole(str, Enum):
    LIMITED = "limited"
    BASIC = "basic"
    ADMIN = "admin"
    CURATOR = "curator"
    GLOBAL_CURATOR = "global_curator"
    SLACK_USER = "slack_user"
    EXT_PERM_USER = "ext_perm_user"

    def is_web_login(self) -> bool:
        return self not in [
            UserRole.SLACK_USER,
            UserRole.EXT_PERM_USER,
            UserRole.LIMITED,
        ]


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    oauth_accounts: list = []
    role: UserRole

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: str
    password: str
    role: UserRole = UserRole.BASIC


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None
    role: UserRole | None = None


# Auth request/response schemas
class SignupRequest(BaseModel):
    email: str
    password: str
    organization: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str