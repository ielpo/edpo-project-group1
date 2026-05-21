"""Distance publisher adapter — publishes distance sensor readings via MQTT."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from simulated_factory.events import EventStore
from simulated_factory.models import SensorConfig

try:
    from paho.mqtt.publish import single as mqtt_publish_single
except ImportError:  # pragma: no cover
    mqtt_publish_single = None  # type: ignore[assignment]


class DistancePublisher:
    """Publishes distance sensor data over MQTT.

    When broker_url is None the publisher is effectively a no-op (useful for
    tests that don't need real MQTT connectivity).
    """

    def __init__(
        self,
        broker_url: str | None,
        event_store: EventStore,
        logger: logging.Logger,
    ):
        self._broker_url = broker_url
        self._event_store = event_store
        self._logger = logger
        self._message_id = 0

    def _build_payload(self, sensor: Any, distance: float) -> dict[str, Any]:
        self._message_id += 1
        cfg = sensor if isinstance(sensor, dict) else getattr(sensor, "__dict__", {})
        # Support both SensorConfig pydantic models and plain dicts
        if hasattr(sensor, "model_dump"):
            cfg = sensor.model_dump()

        return {
            "type": cfg.get("type", "distance_IR_short_left"),
            "UID": cfg.get("uid", cfg.get("UID", "TFu")),
            "location": cfg.get("location", "Conveyor"),
            "messageID": self._message_id,
            "distance": distance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def publish(self, sensor: Any, distance: float) -> None:
        import json

        payload = self._build_payload(sensor, distance)
        topic = "Tinkerforge/Conveyor/distance_IR_short_TFu"
        if hasattr(sensor, "mqtt_topic"):
            topic = sensor.mqtt_topic
        elif isinstance(sensor, dict) and "mqtt_topic" in sensor:
            topic = sensor["mqtt_topic"]

        payload_str = json.dumps(payload)

        await self._event_store.append(
            "MQTT",
            source="distance-publisher",
            message="Published distance",
            topic=topic,
            payload=payload_str,
        )

        if self._broker_url is None or mqtt_publish_single is None:
            return

        from simulated_factory.utils import parse_broker_target

        hostname, port = parse_broker_target(self._broker_url)
        try:
            mqtt_publish_single(topic, payload_str, hostname=hostname, port=port)
        except Exception as exc:
            self._logger.warning(
                "Failed to publish distance to %s:%s: %s", hostname, port, exc
            )
