import re
import json
from typing import Tuple, List, Any


def path_pattern_to_regex(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern)
    # `re.escape` turns `{name}` into `\{name\}`
    regex = re.sub(r"\\\{[^/\\}]+\\\}", r"[^/]+", escaped)
    return re.compile(f"^{regex}$")


# Canonical named-color -> RGB byte mappings (0-255).
CANONICAL_RGB: dict[str, List[int]] = {
    "RED": [255, 0, 0],
    "GREEN": [0, 255, 0],
    "BLUE": [0, 0, 255],
    "YELLOW": [255, 255, 0],
}

# Reverse lookup: tuple(rgb) -> name
_RGB_TO_NAME: dict[tuple[int, ...], str] = {
    tuple(v): k for k, v in CANONICAL_RGB.items()
}

DISTANCE_MIN: float = 0.0
DISTANCE_MAX: float = 30.0


def raw_color_from_name(color: str) -> List[int]:
    return list(CANONICAL_RGB.get(color.upper(), [0, 0, 0]))


def name_from_raw_color(raw_color: List[int]) -> str | None:
    """Return the canonical color name if raw_color exactly matches a preset, else None."""
    return _RGB_TO_NAME.get(tuple(raw_color[:3]))


def rgb_bytes_from_raw(raw_color: List[int]) -> Tuple[int, int, int]:
    padded = (raw_color + [0, 0, 0])[:3]
    return tuple(max(0, min(255, v)) for v in padded)


def validate_distance_range(value: float) -> float:
    """Validate that a distance value is within the supported slider range.

    Raises ValueError if value is outside the inclusive 0.0-30.0 range.
    """
    if value < DISTANCE_MIN or value > DISTANCE_MAX:
        raise ValueError(
            f"Distance value {value} is outside the supported range "
            f"[{DISTANCE_MIN}, {DISTANCE_MAX}]"
        )
    return value


def decode_kafka_value(value: bytes | None) -> Any:
    """Decode a Kafka record value into JSON when possible.

    Returns parsed JSON, decoded text, a raw repr dict for undecodable bytes,
    or None for empty values.
    """
    if value is None:
        return None
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return {"raw": repr(value)}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def decode_kafka_key(key: bytes | None) -> Any:
    """Decode a Kafka record key into text when possible.

    Returns the decoded UTF-8 string, a `repr(bytes(...))` for undecodable
    byte sequences, or `None` when the key is empty.
    """
    if key is None:
        return None
    if isinstance(key, (bytes, bytearray)):
        try:
            return key.decode("utf-8")
        except UnicodeDecodeError:
            return repr(bytes(key))
    return str(key)


def format_sse(data: str, event: str = "update") -> bytes:
    """Format a string as a Server-Sent Events (SSE) message payload.

    Splits the input on newlines and emits `data:` lines per SSE spec, and
    prefixes with an `event:` line. Returns the encoded bytes ready for the
    HTTP response body.
    """
    payload_lines = data.splitlines() or [""]
    body = "\n".join(f"data: {line}" for line in payload_lines)
    return f"event: {event}\n{body}\n\n".encode("utf-8")


def parse_broker_target(url: str) -> tuple[str, int]:
    """Parse an MQTT broker URL into (hostname, port).

    Supports forms like 'tcp://host:port' or plain 'host'.
    Falls back to ('localhost', 1883) when parsing fails.

    Note: bare strings like 'mqtt:1883' are treated as ambiguous by urlparse
    (scheme='mqtt', path='1883'), so the implementation falls back to localhost.
    """
    from urllib.parse import urlparse

    default_port = 1883

    if "://" in url:
        parsed = urlparse(url)
        hostname = parsed.hostname or "localhost"
        port = parsed.port or default_port
        return hostname, port

    # No scheme separator — try urlparse to see if it can resolve a hostname.
    parsed = urlparse(url)
    # urlparse treats "mqtt:1883" as scheme=mqtt, so hostname will be None.
    if parsed.hostname:
        port = parsed.port or default_port
        return parsed.hostname, port

    # Bare string without colon → treat as hostname
    if ":" not in url:
        return url if url else "localhost", default_port

    # Has colon but no scheme separator → ambiguous, fall back to localhost
    # Try to extract port from after the colon
    parts = url.rsplit(":", 1)
    try:
        port = int(parts[1])
    except (ValueError, IndexError):
        port = default_port
    return "localhost", port
