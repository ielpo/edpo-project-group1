from typing import Any

from pydantic import Field

from simulated_factory.models import SensorConfig
from simulated_factory.sensors.base import BaseSensor


class IrSensorConfig(SensorConfig):
    mode: str = "fixed"
    value: Any = None
    scripted_values: list[Any] = Field(default_factory=list)
    sensorId: str = ""


class IrSensor(BaseSensor):
    """Sensor plugin for the infrared (IR) proximity sensor.

    Returns a boolean indicating whether an object is detected.
    Supports both ``fixed`` mode (constant value) and ``scripted`` mode
    (value indexed by the current simulation step).
    """

    def __init__(self, name: str, config: Any) -> None:
        if isinstance(config, dict):
            cfg_dict = dict(config)
            cfg_dict.setdefault("name", name)
            cfg_dict.setdefault("type", "ir")
            cfg_dict.setdefault("sensorId", name)
            cfg = IrSensorConfig(**cfg_dict)
        elif isinstance(config, IrSensorConfig):
            cfg = config
        else:
            cfg = config  # type: ignore[assignment]
        super().__init__(name, cfg)
        self._cfg: IrSensorConfig  # type: ignore[assignment]
        if not self._cfg.sensorId:
            self._cfg.sensorId = name

    def read(self, step: int | None = None) -> bool:
        if step is None:
            step = 0
        if self._cfg.mode == "scripted" and self._cfg.scripted_values:
            index = max(step - 1, 0)
            index = min(index, len(self._cfg.scripted_values) - 1)
            return bool(self._cfg.scripted_values[index])
        return bool(self._cfg.value) if self._cfg.value is not None else True

    def update(self, value: Any) -> None:
        self._cfg.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "mode": self._cfg.mode,
            "value": self._cfg.value,
            "scripted_values": self._cfg.scripted_values,
        }

    def to_sensor_config(self) -> IrSensorConfig:
        return self._cfg.model_copy(deep=True)

    def clone(self) -> "IrSensor":
        return IrSensor(self.name, self._cfg.model_copy(deep=True))

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        filtered = {k: v for k, v in overrides.items() if k != "type"}
        for k, v in filtered.items():
            if hasattr(self._cfg, k):
                setattr(self._cfg, k, v)

    def apply_update_request(self, update: dict[str, Any]) -> None:
        if "value" in update:
            self._cfg.value = update["value"]
        if "mode" in update:
            self._cfg.mode = update["mode"]
        if "scripted_values" in update:
            self._cfg.scripted_values = update["scripted_values"]
