from abc import ABC, abstractmethod
from typing import Any

from models import SensorConfig

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
    def read(self) -> Any:
        """Return the current sensor value. """

    @abstractmethod
    def update(self, value: Any) -> None:
        """Set the sensor value. """

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize the sensor state for API responses."""

class MqttSensor(ABC):
    @abstractmethod
    def get_topic(self) -> str:
        """Get the MQTT topic"""

    @abstractmethod
    def get_payload(self) -> str:
        """Get the serialized payload to publish"""