from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.settings import get_settings
from backend.auth.db_provider import DbAuthProvider
from backend.auth.keycloak_provider import KeycloakAuthProvider
from backend.auth.interfaces import AuthProvider


def get_auth_provider(db: AsyncSession | None = None) -> AuthProvider:
    settings = get_settings()
    if settings.auth_backend == "keycloak":
        return KeycloakAuthProvider()
    # default to DB
    return DbAuthProvider(db) 