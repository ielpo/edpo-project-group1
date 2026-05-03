import logging

from paho.mqtt.publish import single as mqtt_publish_single

from simulated_factory.events import EventStore


class MqttPublisher:
    def __init__(
        self,
        hostname: str,
        port: int,
        event_store: EventStore,
        logger: logging.Logger,
    ):
        self.hostname = hostname
        self.port = port
        self.event_store = event_store
        self.logger = logger
        self._message_id = 1279

    async def publish(self, topic: str, payload: str) -> None:
        await self.event_store.append(
            "MQTT",
            source="simulation-publisher",
            message="Published to MQTT",
            topic=topic,
            payload=payload,
        )

        try:
            mqtt_publish_single(
                topic,
                payload,
                hostname=self.hostname,
                port=self.port,
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to publish MQTT message to %s: %s", self.hostname, exc
            )
