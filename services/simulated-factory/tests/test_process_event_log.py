"""Tests for process event-log filtering, sensor tagging, Kafka observer
ingestion, and rendering of the events fragment.

These tests deliberately avoid spinning up a real Kafka broker. The
KafkaObserver is exercised via an injected fake AIOKafkaConsumer so the
ingestion path can be verified without external services.
"""

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
from simulated_factory.events import (
    ALL_EVENT_TYPES,
    PROCESS_EVENT_TYPES,
    EventStore,
    build_filter_param,
    parse_filter_types,
)


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"


# ---------------------------------------------------------------------------
# 5.1 EventStore filter selection
# ---------------------------------------------------------------------------


async def test_event_store_active_types_returns_only_selected() -> None:
    store = EventStore()
    await store.append("REST", message="noisy poll")
    await store.append("STATE", message="state diff")
    await store.append("MQTT", message="distance publish")
    await store.append("KAFKA", message="kafka msg", topic="info.v1")
    await store.append("COMMAND", message="cmd", payload={"robot": "left"})
    await store.append("SENSOR_REQUEST", message="ir read")

    full, _ = store.list_events()
    process, _ = store.list_events(active_types=PROCESS_EVENT_TYPES)
    subset, _ = store.list_events(active_types=frozenset({"KAFKA", "STATE"}))

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
    assert {item["type"] for item in subset} == {"KAFKA", "STATE"}


async def test_event_store_empty_active_types_returns_no_events() -> None:
    store = EventStore()
    await store.append("KAFKA", message="x", topic="info.v1")
    await store.append("REST", message="y")

    items, _ = store.list_events(active_types=frozenset())
    assert items == []


def test_parse_filter_types_defaults_to_process_when_param_absent() -> None:
    assert parse_filter_types(None) == PROCESS_EVENT_TYPES


def test_parse_filter_types_empty_string_returns_empty_set() -> None:
    assert parse_filter_types("") == frozenset()


def test_parse_filter_types_silently_ignores_unknown_types() -> None:
    result = parse_filter_types("kafka,bogus,command")
    assert result == frozenset({"KAFKA", "COMMAND"})


def test_parse_filter_types_is_case_insensitive() -> None:
    assert parse_filter_types("Kafka,COMMAND") == frozenset({"KAFKA", "COMMAND"})


def test_build_filter_param_lowercase_comma_separated() -> None:
    # Order follows TYPE_LABELS (KAFKA before STATE)
    assert build_filter_param(frozenset({"STATE", "KAFKA"})) == "kafka,state"
    assert build_filter_param(frozenset()) == ""


def test_process_event_types_allowlist_constant() -> None:
    assert PROCESS_EVENT_TYPES == frozenset(
        {"KAFKA", "COMMAND", "PENDING_ACTION", "ACTION_RESOLVED", "SENSOR_REQUEST"}
    )


# ---------------------------------------------------------------------------
# 5.2 SENSOR_REQUEST tagging via middleware
# ---------------------------------------------------------------------------


def _types_for(events: list[dict[str, Any]], endpoint: str) -> list[str]:
    return [e["type"] for e in events if e.get("endpoint") == endpoint]


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


def test_events_fragment_renders_filter_chips() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    # Default (no filter param) = process set
    response = client.get("/fragments/events")
    assert response.status_code == 200
    body = response.text
    # data-active-types holds the active set as comma-separated lowercase
    assert 'data-active-types="kafka,command,pending_action,action_resolved,sensor_request"' in body
    # Preset chips
    assert ">All</a>" in body
    assert ">Process</a>" in body
    assert ">None</a>" in body
    # Individual type chips
    for label in ("Kafka", "Command", "Pending", "Resolved", "Sensor", "REST", "State", "MQTT", "Event"):
        assert ">" + label + "</a>" in body


def test_events_fragment_chip_urls_toggle_active_set() -> None:
    """Each chip's hx-get URL should encode the active set with that type toggled."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    # Active = kafka,command. Clicking the State chip should ADD state.
    body = client.get("/fragments/events?filter=kafka,command").text
    # State chip is inactive -> URL adds 'state'
    assert 'hx-get="/fragments/events?filter=kafka,command,state"' in body
    # Kafka chip is active -> URL removes 'kafka' (leaves 'command')
    assert 'hx-get="/fragments/events?filter=command"' in body
    # Process preset URL
    assert 'hx-get="/fragments/events?filter=kafka,command,pending_action,action_resolved,sensor_request"' in body
    # None preset URL
    assert 'hx-get="/fragments/events?filter="' in body


def test_events_fragment_custom_subset_marks_panel() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    client.get("/api/dobot/left/color")
    client.post(
        "/api/dobot/left/commands",
        json={"type": "suction-cup", "enabled": True},
    )

    # Pick a custom set: only sensor + command
    response = client.get("/fragments/events?filter=sensor_request,command")
    body = response.text
    assert 'id="event-panel"' in body
    assert 'data-active-types="command,sensor_request"' in body
    assert "/api/dobot/left/color" in body


def test_events_fragment_empty_filter_shows_empty_state() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    client.get("/api/dobot/left/color")

    body = client.get("/fragments/events?filter=").text
    assert 'data-active-types=""' in body
    assert "No events match the current filter" in body


def test_events_fragment_unknown_types_silently_ignored() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    body = client.get("/fragments/events?filter=kafka,bogus,command").text
    assert 'data-active-types="kafka,command"' in body


def test_events_fragment_renders_human_readable_command_summary() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

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


def test_events_fragment_process_filter_excludes_rest() -> None:
    """Process filter should exclude REST events from render."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    # Generate mixed events
    client.get("/api/dobot/left/color")  # SENSOR_REQUEST
    client.get("/api/status")  # REST

    body = client.get(
        "/fragments/events?filter=kafka,command,pending_action,action_resolved,sensor_request"
    ).text
    # SENSOR_REQUEST should be present
    assert "/api/dobot/left/color" in body
    # REST events should be excluded by server-side filtering
    assert "event-type-REST" not in body


def test_base_template_contains_client_hook_for_sse_reconnect() -> None:
    """The base template should include the thin client hook that updates
    the URL and reconnects the SSE stream when the event panel is swapped."""
    base_template = (
        Path(__file__).resolve().parents[1] / "templates" / "base.html"
    ).read_text(encoding="utf-8")

    assert "history.replaceState" in base_template
    assert "sse-connect" in base_template
    assert "htmx:afterSwap" in base_template
    assert "htmx.process(body)" in base_template


def test_page_shell_threads_filter_param_into_event_panel_url() -> None:
    """GET / should thread the active filter into the event panel and SSE URLs."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/?filter=kafka,state")
    assert response.status_code == 200
    body = response.text
    assert '/fragments/events?filter=kafka,state' in body
    assert '/sse/status?filter=kafka,state' in body


def test_page_shell_defaults_filter_to_process_set() -> None:
    """GET / without filter param should default to the process set."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    default_param = "kafka,command,pending_action,action_resolved,sensor_request"
    assert f'/fragments/events?filter={default_param}' in body
    assert f'/sse/status?filter={default_param}' in body


def test_page_shell_ignores_unknown_filter_types() -> None:
    """GET / with only unknown types in filter should resolve to an empty set."""
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/?filter=bogus")
    assert response.status_code == 200
    body = response.text
    # All unknowns stripped -> empty active set
    assert '/fragments/events?filter=' in body
    assert '/sse/status?filter=' in body
