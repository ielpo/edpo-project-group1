"""Background poller that caches the Inventory Service grid.

Follows the same start/stop lifecycle as :class:`KafkaObserver`: a background
asyncio task runs independently; connection failures are non-fatal and silently
retried on the next poll cycle.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

DEFAULT_INVENTORY_URL = "http://localhost:8103"
POLL_INTERVAL_SECONDS = 3.0


class InventoryPoller:
    """Polls the Inventory Service and exposes the latest grid via get_cache()."""

    def __init__(
        self,
        *,
        url: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._url = (url or os.getenv("INVENTORY_URL", DEFAULT_INVENTORY_URL)).rstrip(
            "/"
        )
        self._logger = logger or logging.getLogger(__name__)
        self._cache: dict[str, Any] | None = None
        self._task: asyncio.Task[None] | None = None

    def get_cache(self) -> dict[str, Any]:
        if self._cache is None:
            return {"grid": None, "rows": 0, "cols": 0}
        return self._cache

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._poll_loop(), name="inventory-poller")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    async def _poll_loop(self) -> None:
        endpoint = f"{self._url}/inventory"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                while True:
                    try:
                        response = await client.get(endpoint)
                        if response.status_code == 200:
                            self._cache = response.json()
                    except Exception:
                        pass
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise
