from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from simulated_factory.models import SensorConfig, SensorUpdateRequest


class BaseSensor(ABC):
    """Abstract base class all sensor plugins must implement.

    Every plugin receives its raw config dictionary (from config.yml) at
    instantiation.  Internally, each plugin stores a :class:`SensorConfig`
    Pydantic model (``self._cfg``) as the single source of truth for
    configuration data such as mode, scripted values, MQTT metadata, etc.

    Subclasses MUST implement :meth:`read` and :meth:`update`.
    """

    def __init__(self, sensor_id: str, config: dict[str, Any]) -> None:
        from simulated_factory.models import SensorConfig

        self.sensor_id = sensor_id
        # Strip the plugin-routing key so SensorConfig doesn't see an unknown field
        cfg_data = {k: v for k, v in config.items() if k != "type"}
        self._cfg = SensorConfig(sensorId=sensor_id, **cfg_data)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def read(self, step: int = 0) -> Any:
        """Return the current sensor value.

        *step* is the 1-based simulation step index, used by scripted-mode
        plugins to select the appropriate value from ``scripted_values``.
        Custom plugins are free to ignore it.
        """

    @abstractmethod
    def update(self, value: Any) -> None:
        """Set the sensor value directly (called by preset ``sensorUpdates``)."""

    # ------------------------------------------------------------------
    # Shared helpers (used by the engine – override only if needed)
    # ------------------------------------------------------------------

    def apply_update_request(self, update_data: dict[str, Any]) -> None:
        """Apply a dict of field updates (mirrors :class:`SensorUpdateRequest`)."""
        for field_name, value in update_data.items():
            setattr(self._cfg, field_name, value)

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        """Apply preset ``sensor_overrides`` to the internal config."""
        for k, v in overrides.items():
            if k != "type":
                setattr(self._cfg, k, v)

    def clone(self) -> "BaseSensor":
        """Return a deep copy of this plugin (used when forking for a preset run)."""
        new = object.__new__(type(self))
        new.sensor_id = self.sensor_id
        new._cfg = self._cfg.model_copy(deep=True)
        return new

    def to_sensor_config(self) -> "SensorConfig":
        """Return a deep copy of the internal :class:`SensorConfig`."""
        return self._cfg.model_copy(deep=True)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the sensor state for API responses."""
        return self._cfg.model_dump()

    # ------------------------------------------------------------------
    # Convenience properties for backward-compatible attribute access
    # ------------------------------------------------------------------

    @property
    def value(self) -> Any:
        """Shorthand read access to the underlying SensorConfig value."""
        return self._cfg.value

    @value.setter
    def value(self, v: Any) -> None:
        """Shorthand write access to the underlying SensorConfig value."""
        self._cfg.value = v

    @property
    def mode(self) -> str:
        return self._cfg.mode

    @property
    def scripted_values(self) -> list[Any]:
        return self._cfg.scripted_values

    @property
    def raw_color(self) -> list[int]:
        return self._cfg.raw_color
