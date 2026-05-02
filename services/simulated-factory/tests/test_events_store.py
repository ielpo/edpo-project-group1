"""Unit tests for `EventStore` and `EventBridge`.

These tests exercise the in-memory store and the event bridge emission paths
without requiring external services.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
import pytest

from simulated_factory.events import EventBridge, EventStore


async def test_event_store_size_and_clear() -> None:
    store = EventStore(max_entries=5)
    assert store.size() == 0
    await store.append("REST", message="a")
    await store.append("KAFKA", message="b")
    assert store.size() == 2
    items, _ = store.list_events(page_size=10)
    assert len(items) == 2
    store.clear()
    assert store.size() == 0
    items, _ = store.list_events()
    assert items == []


async def test_subscribe_and_unsubscribe_receives_events() -> None:
    store = EventStore(subscriber_queue_size=10)
    q = store.subscribe()
    await store.append("REST", message="hello")
    item = await asyncio.wait_for(q.get(), timeout=0.5)
    assert item["type"] == "REST"

    # After unsubscribe, new events should not be delivered to this queue.
    store.unsubscribe(q)
    await store.append("REST", message="after")
    try:
        got = await asyncio.wait_for(q.get(), timeout=0.05)
    except asyncio.TimeoutError:
        got = None
    assert got is None


async def test_subscriber_queue_size_limits() -> None:
    store = EventStore(subscriber_queue_size=1)
    q = store.subscribe()
    # First append should fill the queue
    await store.append("A", message="1")
    # Second append should be dropped for the subscriber (queue full)
    await store.append("B", message="2")
    item = await asyncio.wait_for(q.get(), timeout=0.5)
    assert item["message"] == "1"
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.get(), timeout=0.05)


async def test_event_bridge_http_mode_emits(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, timeout: float | None = None):
            recorded["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: Any):
            recorded["url"] = url
            recorded["json"] = json
            return None

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    bridge = EventBridge("http", "http://example/cb", logging.getLogger("test"))
    await bridge.emit({"id": "evt-1"})
    assert recorded["url"] == "http://example/cb"
    assert recorded["json"]["id"] == "evt-1"


async def test_event_bridge_none_and_kafka_modes_do_not_raise() -> None:
    bridge_none = EventBridge("none", None, logging.getLogger("test"))
    await bridge_none.emit({"id": "evt-2"})
    bridge_kafka = EventBridge("kafka", None, logging.getLogger("test"))
    await bridge_kafka.emit({"id": "evt-3"})
