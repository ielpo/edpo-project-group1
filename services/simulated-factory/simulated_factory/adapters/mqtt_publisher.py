import logging

try:
    from paho.mqtt.publish import single as mqtt_publish_single
except ImportError:  # pragma: no cover
    mqtt_publish_single = None  # type: ignore[assignment]

from simulated_factory.events import EventStore
from simulated_factory.utils import parse_broker_target


class MqttPublisher:
    def __init__(
        self,
        broker_url: str | None,
        event_store: EventStore,
        logger: logging.Logger,
    ):
        self._broker_url = broker_url
        self._event_store = event_store
        self._logger = logger

    async def publish_raw(self, topic: str, payload: str) -> None:
        await self._event_store.append(
            "MQTT",
            source="simulation-publisher",
            message="Published to MQTT",
            topic=topic,
            payload=payload,
        )

        if self._broker_url is None or mqtt_publish_single is None:
            return

        hostname, port = parse_broker_target(self._broker_url)

        try:
            mqtt_publish_single(
                topic,
                payload,
                hostname=hostname,
                port=port,
            )
        except Exception as exc:
            self._logger.warning(
                "Failed to publish MQTT message to %s:%s: %s", hostname, port, exc
            )
