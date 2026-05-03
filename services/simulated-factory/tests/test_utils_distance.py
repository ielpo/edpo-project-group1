from datetime import datetime
import logging

from simulated_factory.utils import (
    parse_broker_target,
    decode_kafka_value,
    decode_kafka_key,
    format_sse,
    path_pattern_to_regex,
    raw_color_from_name,
    rgb_bytes_from_raw,
)
from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.events import EventStore
from simulated_factory.models import SensorConfig


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
    assert raw_color_from_name("RED") == [1, 0, 0]
    assert raw_color_from_name("unknown") == [0, 0, 0]
    assert rgb_bytes_from_raw([1, 0, 0]) == (255, 0, 0)
    assert rgb_bytes_from_raw([1]) == (255, 0, 0)


def test_distance_publisher_build_payload_messageid_and_fields() -> None:
    dp = DistancePublisher(None, EventStore(), logging.getLogger("test"))
    sensor = SensorConfig(sensorId="distance-1")
    payload1 = dp._build_payload(sensor, 12.34)
    payload2 = dp._build_payload(sensor, 5.0)
    assert isinstance(payload1["messageID"], int)
    assert payload2["messageID"] == payload1["messageID"] + 1
    assert payload1["distance"] == 12.34
    assert payload2["distance"] == 5.0
    # timestamp should be an ISO-formatted datetime
    datetime.fromisoformat(payload1["timestamp"])
