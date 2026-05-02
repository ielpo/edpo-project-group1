from __future__ import annotations

from typing import Any

from simulated_factory.sensors.base import BaseSensor


class IrSensor(BaseSensor):
    """Sensor plugin for the infrared (IR) proximity sensor.

    Returns a boolean indicating whether an object is detected.
    Supports both ``fixed`` mode (constant value) and ``scripted`` mode
    (value indexed by the current simulation step).
    """

    def read(self, step: int = 0) -> bool:
        if self._cfg.mode == "scripted" and self._cfg.scripted_values:
            index = max(step - 1, 0)
            index = min(index, len(self._cfg.scripted_values) - 1)
            return bool(self._cfg.scripted_values[index])
        return bool(self._cfg.value) if self._cfg.value is not None else True

    def update(self, value: Any) -> None:
        self._cfg.value = value
