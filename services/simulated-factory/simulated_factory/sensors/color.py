from __future__ import annotations

from typing import Any

from simulated_factory.sensors.base import BaseSensor
from simulated_factory.utils import raw_color_from_name


class ColorSensor(BaseSensor):
    """Sensor plugin for colour detection.

    Returns the configured colour name and its raw-colour vector.
    Supports both ``fixed`` mode (constant value) and ``scripted`` mode
    (value indexed by the current simulation step).
    """

    def read(self, step: int = 0) -> tuple[str, list[int]]:
        if self._cfg.mode == "scripted" and self._cfg.scripted_values:
            index = max(step - 1, 0)
            index = min(index, len(self._cfg.scripted_values) - 1)
            color = str(self._cfg.scripted_values[index] or "YELLOW").upper()
        else:
            color = str(self._cfg.value or "YELLOW").upper()
        raw_color = self._cfg.raw_color or raw_color_from_name(color)
        return color, raw_color

    def update(self, value: Any) -> None:
        self._cfg.value = value
