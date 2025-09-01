from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Iterable, Dict, List
from datetime import datetime, timedelta

from backend.monitoring import destination_metrics, DestinationStatus

logger = logging.getLogger(__name__)


class DestinationBase(ABC):
    name: str

    def __init__(self) -> None:
        self._last_health_check: datetime | None = None
        self._health_status: bool = True
        self._error_count: int = 0
        self._last_error_time: datetime | None = None

    @abstractmethod
    async def send(self, *, payload: Iterable[Dict[str, Any]], profile_config: dict[str, Any]) -> None:  # noqa: D401
        """Send documents to the destination"""
        ...

    async def send_batch(self, *, documents: List[Dict[str, Any]], profile_config: dict[str, Any], batch_size: int = 50) -> None:
        """Send documents in batches (adapted from Onyx batch processing patterns)"""
        if not documents:
            return

        # Extract organization info for metrics (if available)
        org_id = profile_config.get("organization_id", "unknown")
        cc_pair_id = profile_config.get("cc_pair_id", "unknown")

        # Process in batches like Onyx does
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Start metrics timer
            request_id = destination_metrics.start_request_timer(
                self.name, org_id, "send_batch"
            )
            
            try:
                await self.send(payload=batch, profile_config=profile_config)
                
                # End metrics timer and record success
                duration = destination_metrics.end_request_timer(
                    request_id, self.name, org_id, "send_batch"
                )
                
                # Record batch metrics
                destination_metrics.record_batch_sent(
                    self.name, org_id, cc_pair_id, len(batch), success=True
                )
                
                # Log performance metrics (like Onyx monitoring)
                logger.info(
                    "Batch sent successfully: destination=%s, batch_size=%d, duration=%.2fs",
                    self.name, len(batch), duration
                )
                
                # Reset error count on success
                self._error_count = 0
                
            except Exception as e:
                self._error_count += 1
                self._last_error_time = datetime.utcnow()
                
                # Record error metrics
                destination_metrics.record_error(
                    self.name, org_id, type(e).__name__, cc_pair_id
                )
                destination_metrics.record_batch_sent(
                    self.name, org_id, cc_pair_id, len(batch), success=False
                )
                
                # End timer (even on failure)
                destination_metrics.end_request_timer(
                    request_id, self.name, org_id, "send_batch"
                )
                
                logger.error(
                    "Batch send failed: destination=%s, batch_size=%d, error_count=%d, error=%s",
                    self.name, len(batch), self._error_count, str(e)
                )
                raise

    async def health_check(self, profile_config: dict[str, Any]) -> bool:
        """Check destination health (can be overridden by specific destinations)"""
        org_id = profile_config.get("organization_id", "unknown")
        target_id = profile_config.get("target_id", "unknown")
        
        try:
            # Basic health check - try to send empty payload
            await self.send(payload=[], profile_config=profile_config)
            self._health_status = True
            self._last_health_check = datetime.utcnow()
            
            # Update health metrics
            destination_metrics.update_health_status(
                self.name, org_id, target_id, DestinationStatus.HEALTHY
            )
            
            return True
        except Exception as e:
            self._health_status = False
            self._last_health_check = datetime.utcnow()
            
            # Update health metrics and record error
            destination_metrics.update_health_status(
                self.name, org_id, target_id, DestinationStatus.DOWN
            )
            destination_metrics.record_error(
                self.name, org_id, "health_check_failed"
            )
            
            logger.warning("Health check failed for destination %s: %s", self.name, str(e))
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status and metrics"""
        return {
            "destination": self.name,
            "healthy": self._health_status,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "error_count": self._error_count,
            "last_error_time": self._last_error_time.isoformat() if self._last_error_time else None,
        }

    def config_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": getattr(self, "name", "destination"),
            "type": "object",
            "properties": {},
            "required": [],
        }

    # ------------------------------------------------------------------
    # Enhanced retry helper (adapted from Onyx patterns)
    # ------------------------------------------------------------------

    async def _with_retry(self, coro, max_attempts: int = 5, base_delay: float = 1.0, backoff: float = 2.0):
        """Enhanced retry with exponential backoff (like Onyx @retry decorator)"""
        attempt = 0
        while True:
            try:
                return await coro()
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt >= max_attempts:
                    logger.error("Destination send failed after %s attempts: %s", attempt, exc)
                    raise
                
                # Exponential backoff with jitter (like Onyx)
                delay = base_delay * (backoff ** (attempt - 1))
                jitter = delay * 0.1 * (0.5 - asyncio.get_event_loop().time() % 1)  # Simple jitter
                final_delay = delay + jitter
                
                logger.warning(
                    "Destination send failed (attempt %s/%s), retrying in %.1fs: %s",
                    attempt, max_attempts, final_delay, str(exc)
                )
                await asyncio.sleep(final_delay) 