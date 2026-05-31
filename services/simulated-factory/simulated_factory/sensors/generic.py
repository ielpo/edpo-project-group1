from typing import Any

from simulated_factory.models import SensorConfig
from simulated_factory.sensors.base import BaseSensor


class GenericSensorConfig(SensorConfig):
    value: Any = None


class GenericSensor(BaseSensor):
    """Fallback sensor plugin for sensors whose type cannot be inferred.

    Used as a stand-in when a sensor ID appears in ``sensorUpdates`` or
    is looked up at runtime but was not registered in ``config.yml``.
    Provides a simple value store with no special scripted-mode logic.
    """

    def __init__(self, name: str, config: Any) -> None:
        if isinstance(config, dict):
            cfg_dict = dict(config)
            cfg_dict.setdefault("name", name)
            cfg_dict.setdefault("type", "generic")
            cfg_dict.setdefault("sensorId", name)
            cfg = GenericSensorConfig(**cfg_dict)
        elif isinstance(config, GenericSensorConfig):
            cfg = config
        else:
            cfg = config  # type: ignore[assignment]

        super().__init__(name, cfg)
        self._cfg: GenericSensorConfig  # type: ignore[assignment]
        if not self._cfg.sensorId:
            self._cfg.sensorId = name

    def read(self, step: int = 0) -> Any:
        return self._cfg.value

    def update(self, value: Any) -> None:
        self._cfg.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "value": self._cfg.value,
        }
