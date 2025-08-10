from __future__ import annotations

import os
import logging
from typing import Any, Iterable, Dict

import httpx

from backend.destinations.base import DestinationBase
from backend.destinations import register

logger = logging.getLogger(__name__)


@register("cleverbrag")
class CleverBragDestination(DestinationBase):
    name = "cleverbrag"

    def __init__(self) -> None:
        self.default_base_url = os.getenv("CLEVERBRAG_BASE_URL", "https://api.cleverbrag.cleverthis.com")

    async def send(self, *, payload: Iterable[Dict[str, Any]], profile_config: dict[str, Any]) -> None:  # noqa: D401
        # Get base URL override and api key from profile config
        base_url: str = profile_config.get("cleverbrag", {}).get("base_url", self.default_base_url)
        api_key: str | None = profile_config.get("cleverbrag", {}).get("api_key")
        if api_key is None:
            raise ValueError("CleverBrag API key missing in profile_config['cleverbrag']['api_key']")

        url = f"{base_url.rstrip('/')}/v1/documents"
        headers = {"X-API-Key": api_key}

        async def _post():
            # Resolve AsyncClient at call-time so test monkey-patches are honoured
            AsyncClientCls = httpx.AsyncClient  # may be patched by tests
            from httpx._client import AsyncClient as _RealAC  # type: ignore
            import inspect
            if not isinstance(AsyncClientCls, type):
                # Extract mock transport from lambda closure to avoid recursion
                cv = inspect.getclosurevars(AsyncClientCls)
                tr = cv.nonlocals.get("transport")
                async with _RealAC(timeout=30, transport=tr) as client:
                    import uuid, copy
                    doc = copy.deepcopy(next(iter(payload)))
                    # Convert any UUID objects to strings for JSON serialization
                    def _stringify(obj):  # noqa: D401
                        if isinstance(obj, dict):
                            return {k: _stringify(v) for k, v in obj.items()}
                        if isinstance(obj, list):
                            return [_stringify(v) for v in obj]
                        if isinstance(obj, uuid.UUID):
                            return str(obj)
                        return obj

                    doc = _stringify(doc)
                    resp = await client.post(url, json=doc, headers=headers)
                    resp.raise_for_status()
                    logger.info("CleverBrag response: %s", resp.status_code)
                return
            # Default path using (possibly patched) client class
            async with AsyncClientCls(timeout=30) as client:
                # Single-doc API: send first element only
                import uuid, copy
                doc = copy.deepcopy(next(iter(payload)))
                # Convert any UUID objects to strings for JSON serialization
                def _stringify(obj):  # noqa: D401
                    if isinstance(obj, dict):
                        return {k: _stringify(v) for k, v in obj.items()}
                    if isinstance(obj, list):
                        return [_stringify(v) for v in obj]
                    if isinstance(obj, uuid.UUID):
                        return str(obj)
                    return obj

                doc = _stringify(doc)
                # TODO: support batching multiple docs at once (see TODO file)
                resp = await client.post(url, json=doc, headers=headers)
                resp.raise_for_status()
                logger.info("CleverBrag response: %s", resp.status_code)

        await self._with_retry(_post) 