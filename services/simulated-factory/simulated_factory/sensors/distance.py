import asyncio
from typing import Any, cast
import json

from simulated_factory.sensors.base import BaseSensor, MqttSensor
from simulated_factory.models import SensorConfig


class DistanceSensorConfig(SensorConfig):
    value: float | None = 30.0
    mqtt_topic: str = "Tinkerforge/Conveyor/distance_IR_short_TFu"
    message_type: str = "distance_IR_short_left"
    uid: str = "TFu"
    location: str = "Conveyor"
    message_id: int = 0
    cadence_ms: int = 250
    sensorId: str = ""


class DistanceSensor(BaseSensor, MqttSensor):
    """Sensor plugin for the IR distance sensor on the conveyor."""

    def __init__(self, name: str, config: Any) -> None:
        if isinstance(config, dict):
            cfg_dict = dict(config)
            cfg_dict.setdefault("name", name)
            cfg_dict.setdefault("type", "distance")
            cfg_dict.setdefault("sensorId", name)
            cfg = DistanceSensorConfig(**cfg_dict)
        elif isinstance(config, DistanceSensorConfig):
            cfg = config
        else:
            cfg = config  # type: ignore[assignment]
        super().__init__(name, cfg)
        self._cfg: DistanceSensorConfig = cast(DistanceSensorConfig, self._cfg)
        if not self._cfg.sensorId:
            self._cfg.sensorId = name
        self._message_id = self._cfg.message_id

    def read(self) -> float:
        return self._cfg.value if self._cfg.value is not None else 30.0

    def update(self, value: Any) -> None:
        self._cfg.value = float(value)

    def mqtt_message(self) -> tuple[str, str] | None:
        if self._cfg.value is None:
            return None
        message = {
            "type": self._cfg.type,
            "UID": self._cfg.uid,
            "location": self._cfg.location,
            "messageID": self._message_id,
            "distance": self._cfg.value,
        }
        self._message_id += 1
        return self._cfg.mqtt_topic, json.dumps(message)

    async def start_task(self) -> None:
        interval = self._cfg.cadence_ms / 1000.0
        self._publish_task: asyncio.Task[None] = asyncio.create_task(
            self._publish_loop(interval)
        )

    async def stop_task(self) -> None:
        task = getattr(self, "_publish_task", None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._publish_task = None

    async def _publish_loop(self, interval: float) -> None:
        try:
            while True:
                if getattr(self, "_active", True):
                    await self.publish()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "value": self._cfg.value,
            "mqtt_topic": self._cfg.mqtt_topic,
            "uid": self._cfg.uid,
            "location": self._cfg.location,
        }
