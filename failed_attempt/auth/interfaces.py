from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class TokenPair:
    """Simple container for access & refresh tokens."""

    access_token: str
    refresh_token: str


class AuthProvider(Protocol):
    """Abstract authentication backend used by the API layer."""

    async def signup(self, email: str, password: str, org_name: Optional[str] = None):
        ...

    async def login(self, email: str, password: str) -> TokenPair:  # noqa: D401
        ...

    async def refresh(self, refresh_token: str) -> TokenPair:  # noqa: D401
        ... 