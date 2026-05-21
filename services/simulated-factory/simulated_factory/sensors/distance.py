from typing import cast
import json

from simulated_factory.sensors.base import BaseSensor


class DistanceSensor(BaseSensor):
    """Sensor plugin for the distance / IR-ranging sensor on the conveyor.

    Returns the current distance value in centimetres.
    Supports both ``fixed`` mode (constant value) and ``scripted`` mode
    (value indexed by the current simulation step).

    The underlying ``SensorConfig`` is exposed via :meth:`to_sensor_config`
    so that the ``DistancePublisher`` adapter can build the MQTT payload from
    it without this plugin taking a hard dependency on the publisher.
    """

    def read(self, step: int = 0) -> float:
        if self._cfg.mode == "scripted" and self._cfg.scripted_values:
            index = max(step - 1, 0)
            index = min(index, len(self._cfg.scripted_values) - 1)
            return float(self._cfg.scripted_values[index])
        return float(self._cfg.value) if self._cfg.value is not None else 30.0

    def update(self, value: Any) -> None:
        self._cfg.value = value
