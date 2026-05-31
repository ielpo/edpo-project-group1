import logging

import pytest

from simulated_factory.utils import (
    parse_broker_target,
    decode_kafka_value,
    decode_kafka_key,
    format_sse,
    path_pattern_to_regex,
    raw_color_from_name,
    rgb_bytes_from_raw,
)
from simulated_factory.adapters.mqtt_publisher import MqttPublisher
from simulated_factory.events import EventStore


def test_parse_broker_target_variants() -> None:
    assert parse_broker_target("tcp://mqtt:1883") == ("mqtt", 1883)
    # urlparse treats strings like "mqtt:1883" as having a scheme, so the
    # implementation falls back to localhost when no hostname can be resolved.
    assert parse_broker_target("mqtt:1883") == ("localhost", 1883)
    # Plain hostnames without a colon are returned verbatim and default to 1883.
    assert parse_broker_target("mqtt") == ("mqtt", 1883)
    assert parse_broker_target("mqtt:bad") == ("localhost", 1883)


def test_decode_kafka_value_and_key_and_none() -> None:
    assert decode_kafka_value(None) is None
    assert decode_kafka_value(b'{"a": 1}') == {"a": 1}
    assert decode_kafka_value(b"plain text") == "plain text"
    data = bytes([0xFF, 0xFE])
    assert decode_kafka_value(data) == {"raw": repr(data)}

    assert decode_kafka_key(None) is None
    assert decode_kafka_key(b"ord-1") == "ord-1"
    assert decode_kafka_key(bytes([0xFF, 0xFE])) == repr(bytes([0xFF, 0xFE]))


def test_format_sse_and_multiline() -> None:
    payload = format_sse("line1\nline2", event="update")
    assert isinstance(payload, (bytes, bytearray))
    assert payload.startswith(b"event: update\n")
    assert b"data: line1" in payload and b"data: line2" in payload


def test_path_pattern_to_regex_matches() -> None:
    regex = path_pattern_to_regex("/api/dobot/{name}/commands")
    assert regex.match("/api/dobot/left/commands")
    assert not regex.match("/api/dobot/left/commands/extra")
    assert not regex.match("/api/dobot//commands")


def test_raw_color_and_rgb_helpers() -> None:
    assert raw_color_from_name("RED") == [255, 0, 0]
    assert raw_color_from_name("unknown") == [0, 0, 0]
    assert rgb_bytes_from_raw([255, 0, 0]) == (255, 0, 0)
    assert rgb_bytes_from_raw([128]) == (128, 0, 0)


@pytest.mark.asyncio
async def test_mqtt_publisher_publish_raw_appends_event() -> None:
    event_store = EventStore()
    publisher = MqttPublisher(None, event_store, logging.getLogger("test"))
    await publisher.publish_raw("test/topic", '{"distance": 12.34}')

    items, _ = event_store.list_events(page=1, page_size=10)
    assert len(items) == 1
    assert items[0]["type"] == "MQTT"
    assert items[0]["topic"] == "test/topic"
    assert items[0]["payload"] == '{"distance": 12.34}'
