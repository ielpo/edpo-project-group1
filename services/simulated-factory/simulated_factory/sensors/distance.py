from typing import Any, cast
import json

from pydantic import Field

from simulated_factory.sensors.base import BaseSensor, MqttSensor
from simulated_factory.models import SensorConfig


class DistanceSensorConfig(SensorConfig):
    mode: str = "fixed"
    value: float | None = 30.0
    scripted_values: list[Any] = Field(default_factory=list)
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

    def read(self, step: int | None = None) -> float:
        if step is None:
            return self._cfg.value if self._cfg.value is not None else 30.0
        if self._cfg.mode == "scripted" and self._cfg.scripted_values:
            idx = max(step - 1, 0)
            idx = min(idx, len(self._cfg.scripted_values) - 1)
            return float(self._cfg.scripted_values[idx])
        return self._cfg.value if self._cfg.value is not None else 30.0

    def update(self, value: Any) -> None:
        self._cfg.value = float(value)

    def get_topic(self) -> str:
        return self._cfg.mqtt_topic

    def get_payload(self) -> str:
        message = {
            "type": self._cfg.type,
            "UID": self._cfg.uid,
            "location": self._cfg.location,
            "messageID": self._message_id,
            "distance": self._cfg.value,
        }
        self._message_id += 1
        return json.dumps(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "mode": self._cfg.mode,
            "value": self._cfg.value,
            "mqtt_topic": self._cfg.mqtt_topic,
            "uid": self._cfg.uid,
            "location": self._cfg.location,
        }

    def to_sensor_config(self) -> DistanceSensorConfig:
        cfg = self._cfg.model_copy(deep=True)
        cfg.sensorId = self.name
        return cfg

    def clone(self) -> "DistanceSensor":
        return DistanceSensor(self.name, self._cfg.model_copy(deep=True))

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        filtered = {k: v for k, v in overrides.items() if k != "type"}
        for k, v in filtered.items():
            if hasattr(self._cfg, k):
                setattr(self._cfg, k, v)

    def apply_update_request(self, update: dict[str, Any]) -> None:
        if "value" in update:
            self._cfg.value = float(update["value"])
        if "mode" in update:
            self._cfg.mode = update["mode"]
        if "scripted_values" in update:
            self._cfg.scripted_values = update["scripted_values"]
