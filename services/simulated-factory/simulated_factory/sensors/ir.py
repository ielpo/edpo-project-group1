from typing import Any

from simulated_factory.models import SensorConfig
from simulated_factory.sensors.base import BaseSensor


class IrSensorConfig(SensorConfig):
    value: Any = None
    sensorId: str = ""


class IrSensor(BaseSensor):
    """Sensor plugin for the infrared (IR) proximity sensor.

    Returns a boolean indicating whether an object is detected.
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

    def read(self) -> bool:
        return bool(self._cfg.value) if self._cfg.value is not None else True

    def update(self, value: Any) -> None:
        self._cfg.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "value": self._cfg.value,
        }
