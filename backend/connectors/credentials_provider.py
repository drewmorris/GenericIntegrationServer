from __future__ import annotations

from typing import Any
from types import TracebackType
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import redis  # type: ignore
except Exception:  # noqa: BLE001
    redis = None  # type: ignore

from connectors.onyx.connectors.interfaces import CredentialsProviderInterface  # type: ignore
from backend.db.models import Credential
from backend.security.crypto import maybe_decrypt_dict, encrypt_dict


class DBCredentialsProvider(CredentialsProviderInterface["DBCredentialsProvider"]):
    """Async-session friendly credentials provider with optional Redis locking."""

    def __init__(self, tenant_id: str | None, connector_name: str, credential_id: str, db: AsyncSession):
        self._tenant_id = tenant_id
        self._connector_name = connector_name
        self._credential_id = credential_id
        self._db = db
        self._lock = None
        self._lock_key = f"gis:lock:connector:{connector_name}:cred:{credential_id}"
        self._redis = None
        if redis is not None:
            url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
            if url and url.startswith("redis://"):
                try:
                    self._redis = redis.Redis.from_url(url)
                except Exception:  # noqa: BLE001
                    self._redis = None

    def __enter__(self) -> "DBCredentialsProvider":
        if self._redis is not None:
            self._lock = self._redis.lock(self._lock_key, timeout=900)
            acquired = self._lock.acquire(blocking=True, blocking_timeout=900)
            if not acquired:
                raise RuntimeError(f"Could not acquire lock for key: {self._lock_key}")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._lock is not None:
            try:
                self._lock.release()
            except Exception:  # noqa: BLE001
                pass

    def get_tenant_id(self) -> str | None:
        return self._tenant_id

    def get_provider_key(self) -> str:
        return str(self._credential_id)

    def get_credentials(self) -> dict[str, Any]:
        cred = self._db.sync_session.execute(  # type: ignore[attr-defined]
            select(Credential).where(Credential.id == self._credential_id)
        ).scalar_one()
        return maybe_decrypt_dict(cred.credential_json)

    def set_credentials(self, credential_json: dict[str, Any]) -> None:
        try:
            sess = self._db.sync_session  # type: ignore[attr-defined]
            cred = sess.execute(
                select(Credential).where(Credential.id == self._credential_id).with_for_update()
            ).scalar_one()
            cred.credential_json = encrypt_dict(credential_json)
            sess.commit()
        except Exception:  # noqa: BLE001
            sess.rollback()
            raise

    def is_dynamic(self) -> bool:
        return True


class StaticCredentialsProvider(CredentialsProviderInterface["StaticCredentialsProvider"]):
    def __init__(self, tenant_id: str | None, connector_name: str, credential_json: dict[str, Any]):
        self._tenant_id = tenant_id
        self._connector_name = connector_name
        self._credential_json = credential_json

    def __enter__(self) -> "StaticCredentialsProvider":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass

    def get_tenant_id(self) -> str | None:
        return self._tenant_id

    def get_provider_key(self) -> str:
        return "static"

    def get_credentials(self) -> dict[str, Any]:
        return self._credential_json

    def set_credentials(self, credential_json: dict[str, Any]) -> None:
        self._credential_json = credential_json

    def is_dynamic(self) -> bool:
        return False 