from __future__ import annotations

import asyncio
import logging
import uuid
from collections import deque
from typing import Any, Deque, Optional, Set

import httpx
from fastapi.encoders import jsonable_encoder

from simulated_factory.models import EventEntry


# Event types considered "process-relevant" for the operator-focused view.
# Kept centralized so renderers, filters, and tests share one source of truth.
PROCESS_EVENT_TYPES: frozenset[str] = frozenset(
    {"KAFKA", "COMMAND", "PENDING_ACTION", "ACTION_RESOLVED", "SENSOR_REQUEST"}
)

# Size for the per-subscriber asyncio.Queue used to stream events to UI clients.
EVENT_SUBSCRIBER_QUEUE_SIZE = 100


def _normalize_filter_mode(filter_mode: str | None) -> str:
    if filter_mode is None:
        return "full"
    mode = filter_mode.lower()
    if mode not in ("full", "process"):
        return "full"
    return mode


class EventStore:
    """In-memory event store with lightweight subscriber queues for SSE/SSE-like streams.

    The class preserves existing public methods (`append`, `subscribe`,
    `unsubscribe`, `list_events`) while adding small helpers for tests and
    management (`size`, `clear`)."""

    def __init__(
        self, max_entries: int = 500, subscriber_queue_size: int | None = None
    ):
        self._events: Deque[EventEntry] = deque(maxlen=max_entries)
        self._subscribers: Set[asyncio.Queue] = set()
        self._subscriber_queue_size: int = (
            subscriber_queue_size
            if subscriber_queue_size is not None
            else EVENT_SUBSCRIBER_QUEUE_SIZE
        )

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
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._subscriber_queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def list_events(
        self,
        page: int = 1,
        page_size: int = 50,
        filter_text: str | None = None,
        filter_mode: str | None = None,
    ) -> tuple[list[dict[str, Any]], int | None]:
        items = [jsonable_encoder(item) for item in self._events]
        items.reverse()

        mode = _normalize_filter_mode(filter_mode)
        if mode == "process":
            items = [item for item in items if item.get("type") in PROCESS_EVENT_TYPES]

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

    def size(self) -> int:
        """Return the number of stored events."""
        return len(self._events)

    def clear(self) -> None:
        """Clear stored events. Does not touch subscriber queues."""
        self._events.clear()


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
