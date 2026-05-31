from abc import ABC, abstractmethod
import copy
from typing import Any

from simulated_factory.models import SensorConfig

class BaseSensor(ABC):
    """Abstract base class all sensor plugins must implement.

    Every plugin receives its configuration (from config.yml) at
    instantiation.

    Subclasses MUST implement :meth:`read` and :meth:`update`
    """

    def __init__(self, name: str, config: SensorConfig):
        self.name = name
        self._cfg = config

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def read(self, step: int = 0) -> Any:
        """Return the current sensor value. """

    @abstractmethod
    def update(self, value: Any) -> None:
        """Set the sensor value. """

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize the sensor state for API responses."""

    def clone(self) -> "BaseSensor":
        cfg = self.to_config()
        return self.__class__(self.name, cfg)

    def to_config(self) -> SensorConfig:
        if hasattr(self._cfg, "model_copy"):
            return self._cfg.model_copy(deep=True)
        return copy.deepcopy(self._cfg)

    def apply_update(self, data: dict[str, Any]) -> None:
        filtered = {key: value for key, value in data.items() if key != "type"}
        for key, value in filtered.items():
            if hasattr(self._cfg, key):
                setattr(self._cfg, key, value)

class MqttSensor(ABC):
    @abstractmethod
    def mqtt_message(self) -> tuple[str, str] | None:
        """Return (topic, payload) if the sensor has data to publish."""