"""Tests for process event-log filtering, sensor tagging, Kafka observer
ingestion, and rendering of the events fragment.

These tests deliberately avoid spinning up a real Kafka broker. The
KafkaObserver is exercised via an injected fake AIOKafkaConsumer so the
ingestion path can be verified without external services.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from simulated_factory.adapters.kafka_observer import (
    DEFAULT_BOOTSTRAP_SERVERS,
    DEFAULT_GROUP_ID,
    DEFAULT_TOPICS,
    KafkaObserver,
)
from simulated_factory.api import create_app
from simulated_factory.events import PROCESS_EVENT_TYPES, EventStore


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"


# ---------------------------------------------------------------------------
# 5.1 EventStore filter selection
# ---------------------------------------------------------------------------


async def test_event_store_filter_mode_returns_only_process_types() -> None:
    store = EventStore()
    await store.append("REST", message="noisy poll")
    await store.append("STATE", message="state diff")
    await store.append("MQTT", message="distance publish")
    await store.append("KAFKA", message="kafka msg", topic="info.v1")
    await store.append("COMMAND", message="cmd", payload={"robot": "left"})
    await store.append("SENSOR_REQUEST", message="ir read")

    full, _ = store.list_events()
    process, _ = store.list_events(filter_mode="process")

    assert {item["type"] for item in full} == {
        "REST",
        "STATE",
        "MQTT",
        "KAFKA",
        "COMMAND",
        "SENSOR_REQUEST",
    }
    assert {item["type"] for item in process} == {
        "KAFKA",
        "COMMAND",
        "SENSOR_REQUEST",
    }
    assert all(item["type"] in PROCESS_EVENT_TYPES for item in process)


async def test_event_store_filter_mode_unknown_falls_back_to_full() -> None:
    store = EventStore()
    await store.append("REST", message="x")
    await store.append("KAFKA", message="y", topic="info.v1")

    items, _ = store.list_events(filter_mode="bogus")
    assert {item["type"] for item in items} == {"REST", "KAFKA"}


def test_process_event_types_allowlist_constant() -> None:
    assert PROCESS_EVENT_TYPES == frozenset(
        {"KAFKA", "COMMAND", "PENDING_ACTION", "ACTION_RESOLVED", "SENSOR_REQUEST"}
    )


# ---------------------------------------------------------------------------
# 5.2 SENSOR_REQUEST tagging via middleware
# ---------------------------------------------------------------------------


def _types_for(events: list[dict[str, Any]], endpoint: str) -> list[str]:
    return [e["type"] for e in events if e.get("endpoint") == endpoint]


def _disable_interception(client: TestClient) -> None:
    """Ensure dobot command tests are not held by the interactive intercept set."""
    response = client.put(
        "/api/interactive/config",
        json={"intercepted": [], "timeoutSeconds": 1},
    )
    assert response.status_code == 200


def test_color_endpoint_is_tagged_sensor_request() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/api/dobot/left/color")
    assert response.status_code == 200

    events_response = client.get("/api/events?pageSize=100")
    assert events_response.status_code == 200
    items = events_response.json()["items"]
    types = _types_for(items, "/api/dobot/left/color")
    assert "SENSOR_REQUEST" in types
    assert "REST" not in types


def test_ir_endpoint_is_tagged_sensor_request() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    assert client.get("/api/dobot/left/ir").status_code == 200

    items = client.get("/api/events?pageSize=100").json()["items"]
    types = _types_for(items, "/api/dobot/left/ir")
    assert types == ["SENSOR_REQUEST"]


def test_state_endpoint_is_not_tagged_sensor_request() -> None:
    """Other dobot endpoints must keep using REST so SENSOR_REQUEST remains
    a precise process-relevant signal."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    assert client.get("/api/dobot/left/state").status_code == 200
    items = client.get("/api/events?pageSize=100").json()["items"]
    state_types = _types_for(items, "/api/dobot/left/state")
    assert "SENSOR_REQUEST" not in state_types
    assert "REST" in state_types


# ---------------------------------------------------------------------------
# 5.2/4.2 API filter mode end-to-end
# ---------------------------------------------------------------------------


def test_api_events_filter_mode_excludes_rest_and_state() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)
    _disable_interception(client)

    # Generate a mix of event types
    client.get("/api/dobot/left/color")  # SENSOR_REQUEST
    client.post(
        "/api/dobot/left/commands",
        json={"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}},
    )  # COMMAND + REST capture for the POST itself
    client.get("/api/status")  # REST

    full = client.get("/api/events?pageSize=100").json()["items"]
    process = client.get("/api/events?pageSize=100&mode=process").json()["items"]

    full_types = {e["type"] for e in full}
    process_types = {e["type"] for e in process}

    assert "REST" in full_types
    assert "REST" not in process_types
    assert "SENSOR_REQUEST" in process_types
    assert "COMMAND" in process_types


def test_api_events_default_is_full_history() -> None:
    """Backward compat: callers that do not pass filter mode get every event."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    client.get("/api/status")
    items = client.get("/api/events").json()["items"]
    assert any(e["type"] == "REST" for e in items)


# ---------------------------------------------------------------------------
# 5.3 Kafka observer (mocked consumer)
# ---------------------------------------------------------------------------


class _FakeRecord:
    def __init__(
        self,
        topic: str,
        value: bytes,
        *,
        partition: int = 0,
        offset: int = 0,
        key: bytes | None = None,
    ) -> None:
        self.topic = topic
        self.value = value
        self.partition = partition
        self.offset = offset
        self.key = key


class _FakeAIOKafkaConsumer:
    """Minimal stand-in for aiokafka.AIOKafkaConsumer used in tests."""

    def __init__(self, *topics: str, **kwargs: Any) -> None:
        self.topics = topics
        self.kwargs = kwargs
        self._records: list[_FakeRecord] = []
        self._signal: asyncio.Event = asyncio.Event()
        self._stopped = False

    def queue(self, record: _FakeRecord) -> None:
        self._records.append(record)
        self._signal.set()

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        self._stopped = True
        self._signal.set()

    def __aiter__(self) -> "_FakeAIOKafkaConsumer":
        return self

    async def __anext__(self) -> _FakeRecord:
        while not self._records:
            if self._stopped:
                raise StopAsyncIteration
            await self._signal.wait()
            self._signal.clear()
        return self._records.pop(0)


async def test_kafka_observer_appends_kafka_events_for_consumed_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIMULATED_FACTORY_KAFKA_OBSERVER", "enabled")

    store = EventStore()
    fake_consumer_holder: dict[str, _FakeAIOKafkaConsumer] = {}

    def factory(*topics: str, **kwargs: Any) -> _FakeAIOKafkaConsumer:
        consumer = _FakeAIOKafkaConsumer(*topics, **kwargs)
        fake_consumer_holder["consumer"] = consumer
        return consumer

    observer = KafkaObserver(
        event_store=store,
        logger=logging.getLogger("test-observer"),
        consumer_factory=factory,
    )
    await observer.start()
    # Allow the background task to call consumer.start()
    for _ in range(20):
        if "consumer" in fake_consumer_holder:
            break
        await asyncio.sleep(0.01)
    assert "consumer" in fake_consumer_holder, "factory was not invoked"
    consumer = fake_consumer_holder["consumer"]

    consumer.queue(
        _FakeRecord(
            "order.manufacture.v1",
            b'{"orderId": "ord-1", "color": "RED"}',
            partition=2,
            offset=42,
            key=b"ord-1",
        )
    )

    # Wait for the observer to drain the queued record
    for _ in range(50):
        full, _ = store.list_events()
        if full:
            break
        await asyncio.sleep(0.02)

    full, _ = store.list_events()
    await observer.stop()

    kafka_events = [e for e in full if e["type"] == "KAFKA"]
    assert kafka_events, "Kafka observer should append a KAFKA event"
    event = kafka_events[0]
    assert event["topic"] == "order.manufacture.v1"
    payload = event["payload"]
    assert payload["topic"] == "order.manufacture.v1"
    assert payload["partition"] == 2
    assert payload["offset"] == 42
    assert payload["key"] == "ord-1"
    assert payload["value"] == {"orderId": "ord-1", "color": "RED"}


async def test_kafka_observer_uses_fixed_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIMULATED_FACTORY_KAFKA_OBSERVER", "enabled")

    captured: dict[str, Any] = {}

    def factory(*topics: str, **kwargs: Any) -> _FakeAIOKafkaConsumer:
        captured["topics"] = topics
        captured["kwargs"] = kwargs
        return _FakeAIOKafkaConsumer(*topics, **kwargs)

    observer = KafkaObserver(
        event_store=EventStore(),
        logger=logging.getLogger("test-observer-defaults"),
        consumer_factory=factory,
    )
    await observer.start()
    for _ in range(20):
        if captured:
            break
        await asyncio.sleep(0.01)
    await observer.stop()

    assert set(captured["topics"]) == set(DEFAULT_TOPICS)
    assert captured["kwargs"]["bootstrap_servers"] == DEFAULT_BOOTSTRAP_SERVERS
    assert captured["kwargs"]["group_id"] == DEFAULT_GROUP_ID


async def test_kafka_observer_disabled_via_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIMULATED_FACTORY_KAFKA_OBSERVER", "disabled")

    called = {"factory": False}

    def factory(*topics: str, **kwargs: Any) -> _FakeAIOKafkaConsumer:
        called["factory"] = True
        return _FakeAIOKafkaConsumer(*topics, **kwargs)

    observer = KafkaObserver(
        event_store=EventStore(),
        logger=logging.getLogger("test-observer-disabled"),
        consumer_factory=factory,
    )
    await observer.start()
    await observer.stop()
    assert called["factory"] is False


async def test_kafka_observer_connection_failure_is_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIMULATED_FACTORY_KAFKA_OBSERVER", "enabled")

    class _FailingConsumer(_FakeAIOKafkaConsumer):
        async def start(self) -> None:  # type: ignore[override]
            raise RuntimeError("simulated connection failure")

    observer = KafkaObserver(
        event_store=EventStore(),
        logger=logging.getLogger("test-observer-failure"),
        consumer_factory=lambda *t, **k: _FailingConsumer(*t, **k),
    )
    # Should not raise even though the underlying consumer.start() throws
    await observer.start()
    # Drain background task
    for _ in range(20):
        if not observer._running:
            break
        await asyncio.sleep(0.01)
    await observer.stop()
    assert observer._consumer is None


# ---------------------------------------------------------------------------
# 5.4 Fragment toggle and rendering
# ---------------------------------------------------------------------------


def test_events_fragment_renders_filter_toggles() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/fragments/events")
    assert response.status_code == 200
    body = response.text
    assert 'data-filter-mode="full"' in body
    assert 'data-filter-mode="process"' in body
    assert "Full log" in body
    assert "Process view" in body


def test_events_fragment_process_mode_marks_panel() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)
    _disable_interception(client)

    # Generate some events
    client.get("/api/dobot/left/color")
    client.post(
        "/api/dobot/left/commands",
        json={"type": "suction-cup", "enabled": True},
    )

    response = client.get("/fragments/events?filter=process")
    body = response.text
    assert 'id="event-panel"' in body
    assert 'data-filter-mode="process"' in body
    # Process-mode rendering produces a sensor endpoint indicator
    assert "/api/dobot/left/color" in body


def test_events_fragment_renders_human_readable_command_summary() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)
    _disable_interception(client)

    client.post(
        "/api/dobot/left/commands",
        json={"type": "move", "target": {"x": 11, "y": 22, "z": 33, "r": 0}},
    )
    client.post(
        "/api/dobot/left/commands",
        json={"type": "suction-cup", "enabled": True},
    )

    body = client.get("/fragments/events").text
    # Move command summary
    assert "x=11" in body and "y=22" in body and "z=33" in body
    # Suction cup ON state
    assert "ON" in body
    # Raw payload disclosure available for debugging
    assert "<details" in body and "Raw payload" in body


def test_events_fragment_marks_process_event_class() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)
    _disable_interception(client)

    client.post(
        "/api/dobot/left/commands",
        json={"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}},
    )
    body = client.get("/fragments/events").text
    # Articles are tagged so client-side toggle can hide non-process entries
    assert "event-process" in body
    assert "event-type-COMMAND" in body
