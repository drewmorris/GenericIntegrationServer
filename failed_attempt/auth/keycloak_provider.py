from __future__ import annotations

from backend.auth.interfaces import AuthProvider, TokenPair


class KeycloakAuthProvider(AuthProvider):
    """Placeholder for future Keycloak integration."""

    async def signup(self, email: str, password: str, org_name: str | None = None):  # noqa: D401
        raise NotImplementedError("Keycloak signup not implemented yet")

    async def login(self, email: str, password: str) -> TokenPair:  # noqa: D401
        raise NotImplementedError("Keycloak login not implemented yet")

    async def refresh(self, refresh_token: str) -> TokenPair:  # noqa: D401
        raise NotImplementedError("Keycloak refresh not implemented yet") 