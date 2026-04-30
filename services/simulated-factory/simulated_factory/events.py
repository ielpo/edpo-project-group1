from __future__ import annotations

import asyncio
import logging
import uuid
from collections import deque
from typing import Any

import httpx
from fastapi.encoders import jsonable_encoder

from simulated_factory.models import EventEntry


class EventStore:
    def __init__(self, max_entries: int = 500):
        self._events: deque[EventEntry] = deque(maxlen=max_entries)
        self._subscribers: set[asyncio.Queue] = set()

    async def append(
        self,
        event_type: str,
        *,
        source: str | None = None,
        message: str | None = None,
        topic: str | None = None,
        endpoint: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        payload: Any = None,
    ) -> EventEntry:
        entry = EventEntry(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            type=event_type,
            source=source,
            message=message,
            topic=topic,
            endpoint=endpoint,
            method=method,
            statusCode=status_code,
            payload=payload,
        )
        self._events.append(entry)
        encoded = jsonable_encoder(entry)
        for subscriber in list(self._subscribers):
            try:
                subscriber.put_nowait(encoded)
            except asyncio.QueueFull:
                continue
        return entry

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def list_events(
        self, page: int = 1, page_size: int = 50, filter_text: str | None = None
    ) -> tuple[list[dict[str, Any]], int | None]:
        items = [jsonable_encoder(item) for item in self._events]
        items.reverse()
        if filter_text:
            needle = filter_text.lower()
            filtered: list[dict[str, Any]] = []
            for item in items:
                haystack = " ".join(
                    str(item.get(field, ""))
                    for field in ("type", "topic", "endpoint", "method", "message")
                ).lower()
                if needle in haystack:
                    filtered.append(item)
            items = filtered

        start = max(page - 1, 0) * page_size
        end = start + page_size
        next_page = page + 1 if end < len(items) else None
        return items[start:end], next_page


class EventBridge:
    def __init__(self, mode: str, target_url: str | None, logger: logging.Logger):
        self.mode = mode
        self.target_url = target_url
        self.logger = logger

    async def emit(self, payload: dict[str, Any]) -> None:
        if self.mode == "none":
            return

        if self.mode == "http":
            if not self.target_url:
                self.logger.warning(
                    "Event bridge is enabled for HTTP mode, but SIMULATOR_EVENT_BRIDGE_URL is unset"
                )
                return
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    await client.post(self.target_url, json=payload)
            except httpx.HTTPError as exc:
                self.logger.warning("Failed to emit event bridge callback: %s", exc)
            return

        if self.mode == "kafka":
            self.logger.info(
                "Kafka event bridge requested. Event retained locally for MVP compatibility: %s",
                payload.get("id"),
            )
            return

        self.logger.warning("Unknown event bridge mode %s ignored", self.mode)
