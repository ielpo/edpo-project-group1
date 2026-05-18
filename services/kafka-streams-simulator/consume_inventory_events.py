"""Console subscriber for inventory Kafka events.

Usage examples:
  uv run consume_inventory_events.py
  uv run consume_inventory_events.py --from-beginning
  uv run consume_inventory_events.py --topic sensor.block-detected.v1
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from typing import Any

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

DEFAULT_BOOTSTRAP_SERVER = "localhost:9092"
DEFAULT_TOPIC = "inventory.blocks.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Subscribe to Kafka topics and print events in the console."
    )
    parser.add_argument(
        "--bootstrap-server",
        default=DEFAULT_BOOTSTRAP_SERVER,
        help=f"Kafka bootstrap server (default: {DEFAULT_BOOTSTRAP_SERVER})",
    )
    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help=f"Topic to subscribe to (default: {DEFAULT_TOPIC})",
    )
    parser.add_argument(
        "--group-id",
        help="Optional consumer group id. A random one is generated if omitted.",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Read the topic from the earliest available offset.",
    )
    return parser.parse_args()


def decode_bytes(value: bytes | None) -> str:
    if value is None:
        return "null"
    return value.decode("utf-8", errors="replace")


def format_payload(raw_value: bytes | None) -> str:
    text = decode_bytes(raw_value)
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(payload, indent=2, sort_keys=True)


def format_timestamp(timestamp_ms: int | None) -> str:
    if not timestamp_ms:
        return "unknown"
    return datetime.fromtimestamp(timestamp_ms / 1000).isoformat(timespec="seconds")


def main() -> int:
    args = parse_args()
    group_id = args.group_id or f"inventory-console-{uuid.uuid4().hex[:8]}"

    print(f"Kafka bootstrap server: {args.bootstrap_server}")
    print(f"Topic: {args.topic}")
    print(f"Consumer group: {group_id}")
    print(
        "Offset mode: "
        + ("earliest (--from-beginning)" if args.from_beginning else "latest (new events only)")
    )
    print("Waiting for events... Press Ctrl+C to stop.\n")

    try:
        consumer = KafkaConsumer(
            args.topic,
            bootstrap_servers=args.bootstrap_server,
            group_id=group_id,
            auto_offset_reset="earliest" if args.from_beginning else "latest",
            enable_auto_commit=False,
        )
    except NoBrokersAvailable:
        print(
            f"Could not connect to Kafka at {args.bootstrap_server}. "
            "Make sure Kafka is running first.",
            file=sys.stderr,
        )
        return 1

    try:
        for message in consumer:
            print("-" * 80)
            print(
                f"topic={message.topic} partition={message.partition} offset={message.offset} "
                f"timestamp={format_timestamp(message.timestamp)}"
            )
            print(f"key={decode_bytes(message.key)}")
            print("value=")
            print(format_payload(message.value))
            print(flush=True)
    except KeyboardInterrupt:
        print("\nStopped subscriber.")
        return 0
    finally:
        consumer.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

