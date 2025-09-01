from __future__ import annotations

import os
import logging
from typing import Iterable, Dict, Any

import httpx

from backend.destinations.base import DestinationBase
from backend.destinations import register

logger = logging.getLogger(__name__)


@register("onyx")
class OnyxDestination(DestinationBase):
    name = "onyx"

    def __init__(self) -> None:
        super().__init__()  # Initialize base class attributes
        self.default_base_url = os.getenv("ONYX_BASE_URL", "https://api.onyx.com")

    async def send(self, *, payload: Iterable[Dict[str, Any]], profile_config: dict[str, Any]) -> None:  # noqa: D401
        cfg = profile_config.get("onyx", {})
        base_url: str = cfg.get("base_url", self.default_base_url)
        api_key: str | None = cfg.get("api_key")
        if api_key is None:
            raise ValueError("Onyx API key missing in profile config")

        url = f"{base_url.rstrip('/')}/v1/documents"
        headers = {"Authorization": f"Bearer {api_key}"}

        async def _post():
            async with httpx.AsyncClient(timeout=30) as client:
                doc = next(iter(payload))
                resp = await client.post(url, json=doc, headers=headers)
                resp.raise_for_status()
                logger.info("Onyx response: %s", resp.status_code)

        await self._with_retry(_post) 