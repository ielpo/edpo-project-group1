from typing import cast
import json

from simulated_factory.sensors.base import BaseSensor, MqttSensor
from simulated_factory.models import SensorConfig

class DistanceSensorConfig(SensorConfig):
    value: float = 30.0
    mqtt_topic: str = "Tinkerforge/Conveyor/distance_IR_short_TFu"
    message_type: str = "distance_IR_short_left"
    uid: str = "TFu"
    location: str = "Conveyor"
    message_id: int = 0

class DistanceSensor(BaseSensor, MqttSensor):
    """Sensor plugin for the IR distance sensor on the conveyor. """

    def __init__(self, name: str, config: SensorConfig) -> None:
        super().__init__(name, config)
        self._cfg = cast(DistanceSensorConfig, self._cfg)

    def read(self) -> float:
        return self._cfg.value

    def update(self, value: float) -> None:
        self._cfg.value = value

    def get_topic(self) -> str:
        return self._cfg.mqtt_topic

    def get_payload(self) -> str:
        message = {
            "type": self._cfg.type,
            "UID": self._cfg.uid,
            "location": self._cfg.location,
            "messageID": self._cfg.message_id,
            "distance": self._cfg.value,
        }
        self._message_id += 1

        return json.dumps(message)
