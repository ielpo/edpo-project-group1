from __future__ import annotations

import json
import logging
from typing import Any

from paho.mqtt.publish import single as mqtt_publish_single

from simulated_factory.utils import parse_broker_target

from simulated_factory.events import EventStore
from simulated_factory.models import SensorConfig, utc_now


class DistancePublisher:
    def __init__(
        self,
        broker_url: str | None,
        event_store: EventStore,
        logger: logging.Logger,
    ):
        self.broker_url = broker_url
        self.event_store = event_store
        self.logger = logger
        self._message_id = 1279

    async def publish(self, sensor: SensorConfig, distance: float) -> dict[str, Any]:
        topic = (
            sensor.mqtt_topic
            or f"sensors/distance/{sensor.location}/{sensor.message_type}"
        )
        payload = self._build_payload(sensor, distance)

        await self.event_store.append(
            "MQTT",
            source="distance-publisher",
            message="Published distance sensor reading",
            topic=topic,
            payload=payload,
        )

        if self.broker_url:
            try:
                hostname, port = parse_broker_target(self.broker_url)
                mqtt_publish_single(
                    topic,
                    json.dumps(payload),
                    hostname=hostname,
                    port=port,
                )
            except Exception as exc:
                self.logger.warning(
                    "Failed to publish MQTT message to %s: %s", self.broker_url, exc
                )

        return payload

    def _build_payload(self, sensor: SensorConfig, distance: float) -> dict[str, Any]:
        """Construct the MQTT payload for a distance sensor reading.

        This helper centralizes the payload shape so tests can assert on the
        produced structure without duplicating construction logic.
        """
        pid = self._message_id
        self._message_id += 1
        return {
            "type": sensor.message_type,
            "UID": sensor.uid,
            "location": sensor.location,
            "messageID": pid,
            "distance": distance,
            "timestamp": utc_now().isoformat(),
        }

    # Broker parsing moved to simulated_factory.utils.parse_broker_target
