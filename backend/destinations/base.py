from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Iterable, Dict

logger = logging.getLogger(__name__)


class DestinationBase(ABC):
    name: str

    @abstractmethod
    async def send(self, *, payload: Iterable[Dict[str, Any]], profile_config: dict[str, Any]) -> None:  # noqa: D401
        ...

    def config_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": getattr(self, "name", "destination"),
            "type": "object",
            "properties": {},
            "required": [],
        }

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _with_retry(self, coro, max_attempts: int = 3, base_delay: float = 1.0):
        attempt = 0
        while True:
            try:
                return await coro()
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt >= max_attempts:
                    logger.error("Destination send failed after %s attempts: %s", attempt, exc)
                    raise
                delay = base_delay * 2 ** (attempt - 1)
                logger.warning("Destination send failed (attempt %s), retrying in %.1fs", attempt, delay)
                await asyncio.sleep(delay) 