"""Database‐backed authentication provider.

This, along with migrations & models, will evolve during Phase 1 but a stub is
useful so the rest of the application can import it safely.
"""
from __future__ import annotations

import uuid

from jose import jwt
from typing import Optional

from backend.auth.interfaces import AuthProvider, TokenPair
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa

from backend.db.models import User, Organization
from backend.auth.crypto import hash_password, verify_password
from backend.settings import get_settings

settings = get_settings()


# Temporary in-memory user representation for tests
class SimpleUser:
    id: uuid.UUID
    email: str
    hashed_pw: str

    def __init__(self, email: str, hashed_pw: str):
        self.id = uuid.uuid4()
        self.email = email
        self.hashed_pw = hashed_pw


class DbAuthProvider(AuthProvider):
    """Authentication provider backed by SQLAlchemy async session.

    If instantiated without a session it falls back to the previous in-memory behaviour
    (handy for unit tests).
    """

    def __init__(self, db: AsyncSession | None = None):
        self._db = db
        # fallback memory store
        self._users: dict[str, SimpleUser] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def signup(self, email: str, password: str, org_name: Optional[str] = None):
        if self._db is None:
            return await self._signup_in_mem(email, password)
        return await self._signup_db(email, password, org_name)

    async def login(self, email: str, password: str) -> TokenPair:  # type: ignore[override]
        if self._db is None:
            return await self._login_in_mem(email, password)
        return await self._login_db(email, password)

    async def refresh(self, refresh_token: str) -> TokenPair:  # type: ignore[override]
        # refresh flow identical for both stores – we only need to know the email
        try:
            payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Invalid refresh token") from exc
        subj = payload.get("sub")
        if subj is None:
            raise ValueError("Invalid refresh token payload")

        if self._db is None:
            # issue new tokens directly
            if subj not in self._users:
                raise ValueError("User not found")
            return self._issue_tokens(subj)

        return await self.login(subj, "_dummy_")

    async def revoke(self, refresh_token: str) -> None:
        """Invalidate a refresh token (logout)."""
        if self._db is None:
            return  # noop for in-memory

        from backend.db.models import UserToken

        try:
            payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except Exception:
            return
        jti = payload.get("jti")
        if jti is None:
            return
        await self._db.execute(sa.delete(UserToken).where(UserToken.refresh_token_jti == jti))
        await self._db.commit()

    # ------------------------------------------------------------------
    # Internal helpers – DB backed
    # ------------------------------------------------------------------

    async def _signup_db(self, email: str, password: str, org_name: Optional[str]):
        assert self._db is not None
        # create org lazily if provided
        org_id: uuid.UUID
        if org_name is not None:
            result = await self._db.execute(select(Organization).where(Organization.name == org_name))
            org = result.scalar_one_or_none()
            if org is None:
                org = Organization(name=org_name)
                self._db.add(org)
                await self._db.flush()
            org_id = org.id
        else:
            # use first org or raise
            result = await self._db.execute(select(Organization))
            org = result.scalars().first()
            if org is None:
                raise ValueError("No organization exists, provide org_name")
            org_id = org.id

        hashed = hash_password(password)
        # prevent duplicate users (unique index may raise otherwise)
        existing = await self._db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise ValueError("User already exists")
        user = User(email=email, hashed_pw=hashed, organization_id=org_id)
        self._db.add(user)
        await self._db.commit()
        return user

    async def _login_db(self, email: str, password: str) -> TokenPair:
        assert self._db is not None
        result = await self._db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_pw):
            raise ValueError("Invalid credentials")
        return self._issue_tokens(user.email)

    # ------------------------------------------------------------------
    # Internal helpers – in-memory fallback (unchanged logic)
    # ------------------------------------------------------------------

    async def _signup_in_mem(self, email: str, password: str):
        if email in self._users:
            raise ValueError("User already exists")
        hashed = hash_password(password)
        user = SimpleUser(email=email, hashed_pw=hashed)
        self._users[email] = user
        return user

    async def _login_in_mem(self, email: str, password: str) -> TokenPair:
        user = self._users.get(email)
        if not user or not verify_password(password, user.hashed_pw):
            raise ValueError("Invalid credentials")
        return self._issue_tokens(user.email)

    # ------------------------------------------------------------------
    # Token helper
    # ------------------------------------------------------------------

    def _issue_tokens(self, subject_email: str) -> TokenPair:
        from datetime import datetime, timedelta
        from jose import jwt

        now = datetime.utcnow()
        jti = str(uuid.uuid4())
        access_payload = {
            "sub": subject_email,
            "exp": now + timedelta(minutes=settings.access_ttl_minutes),
            "iat": now,
        }
        refresh_payload = {
            "sub": subject_email,
            "jti": jti,
            "exp": now + timedelta(days=settings.refresh_ttl_days),
            "iat": now,
        }
        access_token = jwt.encode(access_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        # Persist refresh token if DB available – use a separate session to avoid
        # concurrent operations on the request-bound session.
        if self._db is not None:
            from backend.db.models import UserToken, User  # local import to avoid circular

            async def _store():  # inner coroutine using independent session
                try:
                    from backend.db.session import AsyncSessionLocal
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(select(User).where(User.email == subject_email))
                        user = result.scalar_one()
                        token_row = UserToken(
                            id=uuid.uuid4(),
                            user_id=user.id,
                            refresh_token_jti=jti,
                            expires_at=now + timedelta(days=settings.refresh_ttl_days),
                            created_at=now,
                        )
                        session.add(token_row)
                        await session.commit()
                except Exception:
                    # Best-effort; token persistence failure should not break login/signup
                    return

            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_store())
                else:
                    loop.run_until_complete(_store())
            except RuntimeError:
                # No event loop – run directly
                import asyncio as _asyncio
                _asyncio.run(_store())

        return TokenPair(access_token=access_token, refresh_token=refresh_token) 