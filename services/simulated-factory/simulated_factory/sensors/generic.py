from __future__ import annotations

from typing import Any

from simulated_factory.sensors.base import BaseSensor


class GenericSensor(BaseSensor):
    """Fallback sensor plugin for sensors whose type cannot be inferred.

    Used as a stand-in when a sensor ID appears in ``sensorUpdates`` or
    is looked up at runtime but was not registered in ``config.yml``.
    Provides a simple value store with no special scripted-mode logic.
    """

    def read(self, step: int = 0) -> Any:
        return self._cfg.value

    def update(self, value: Any) -> None:
        self._cfg.value = value
