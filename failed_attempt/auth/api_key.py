import hashlib
import secrets
import uuid

from fastapi import Request
from pydantic import BaseModel

from backend.auth.schemas import UserRole


_API_KEY_HEADER_NAME = "Authorization"
_API_KEY_HEADER_ALTERNATIVE_NAME = "X-Backend-Authorization"
_BEARER_PREFIX = "Bearer "
_API_KEY_PREFIX = "bk_"  # backend key prefix
_API_KEY_LEN = 192
API_KEY_HASH_ROUNDS = 100000


class ApiKeyDescriptor(BaseModel):
    api_key_id: int
    api_key_display: str
    api_key: str | None = None  # only present on initial creation
    api_key_name: str | None = None
    api_key_role: UserRole

    user_id: uuid.UUID


def generate_api_key(tenant_id: str | None = None) -> str:
    # For now, simple key generation (multi-tenant support later)
    return _API_KEY_PREFIX + secrets.token_urlsafe(_API_KEY_LEN)


def hash_api_key(api_key: str) -> str:
    # NOTE: no salt is needed, as the API key is randomly generated
    # and overlaps are impossible
    if api_key.startswith(_API_KEY_PREFIX):
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    raise ValueError(f"Invalid API key prefix: {api_key[:3]}")


def build_displayable_api_key(api_key: str) -> str:
    if api_key.startswith(_API_KEY_PREFIX):
        api_key = api_key[len(_API_KEY_PREFIX) :]

    return _API_KEY_PREFIX + api_key[:4] + "********" + api_key[-4:]


def get_hashed_api_key_from_request(request: Request) -> str | None:
    raw_api_key_header = request.headers.get(
        _API_KEY_HEADER_ALTERNATIVE_NAME
    ) or request.headers.get(_API_KEY_HEADER_NAME)
    if raw_api_key_header is None:
        return None

    if raw_api_key_header.startswith(_BEARER_PREFIX):
        raw_api_key_header = raw_api_key_header[len(_BEARER_PREFIX) :].strip()

    return hash_api_key(raw_api_key_header)
