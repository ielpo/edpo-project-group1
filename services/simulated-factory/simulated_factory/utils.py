import re
import json
from typing import Tuple, List, Any


def path_pattern_to_regex(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern)
    # `re.escape` turns `{name}` into `\{name\}`
    regex = re.sub(r"\\\{[^/\\}]+\\\}", r"[^/]+", escaped)
    return re.compile(f"^{regex}$")


def raw_color_from_name(color: str) -> List[int]:
    palette = {
        "RED": [1, 0, 0],
        "GREEN": [0, 1, 0],
        "BLUE": [0, 0, 1],
        "YELLOW": [1, 1, 0],
    }
    return palette.get(color.upper(), [0, 0, 0])


def rgb_bytes_from_raw(raw_color: List[int]) -> Tuple[int, int, int]:
    padded = (raw_color + [0, 0, 0])[:3]
    return tuple(255 if value else 0 for value in padded)


def parse_broker_target(broker_url: str) -> tuple[str, int]:
    """Parse a broker URL or host[:port] into (hostname, port).

    Accepts full URLs (with scheme) or plain host[:port] strings. Falls
    back to localhost:1883 when no port or hostname can be resolved.
    """
    from urllib.parse import urlparse

    parsed = urlparse(broker_url)
    if parsed.scheme:
        return parsed.hostname or "localhost", parsed.port or 1883

    if ":" in broker_url:
        host, port = broker_url.rsplit(":", 1)
        try:
            return host, int(port)
        except Exception:
            return host, 1883

    return broker_url, 1883


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
