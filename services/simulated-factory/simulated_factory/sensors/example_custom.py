"""
Example custom sensor plugin for the simulated-factory service.

This file demonstrates how to create a custom sensor.  Copy this file,
rename it (e.g. ``temperature.py``), adjust the class name to match the
naming convention (``TemperatureSensor``), and register it in ``config.yml``.

Naming convention:
  - File:   simulated_factory/sensors/<type>.py  (underscores for multi-word)
  - Class:  <TitleCase of type> + "Sensor"
  - Config: ``type: <type>`` (hyphenated kebab-case is allowed, maps to underscores)

  Example for type "temperature":
    File:   simulated_factory/sensors/temperature.py
    Class:  TemperatureSensor
    Config: type: temperature

  Example for type "my-custom":
    File:   simulated_factory/sensors/my_custom.py
    Class:  MyCustomSensor
    Config: type: my-custom
"""
from __future__ import annotations

import random
from typing import Any

from simulated_factory.sensors.base import BaseSensor


class ExampleCustomSensor(BaseSensor):
    """A synthetic sensor that reports a randomly drifting float value.

    This plugin demonstrates a sensor with its own internal state that goes
    beyond the standard fixed/scripted modes provided by the base class.

    To use this sensor, add to ``config.yml``::

        defaults:
          sensors:
            my-random-sensor:
              type: example-custom     # maps to this file (example_custom.py)
              base_value: 50.0         # custom config key read in __init__
              drift_range: 5.0         # custom config key

    Then the engine will load this file and instantiate ``ExampleCustomSensor``.
    """

    def __init__(self, sensor_id: str, config: dict[str, Any]) -> None:
        super().__init__(sensor_id, config)
        # Custom fields from config.yml are available on self._cfg as well
        # as in the raw config dict passed to __init__.
        self._base_value: float = float(config.get("base_value", 50.0))
        self._drift_range: float = float(config.get("drift_range", 5.0))
        self._current: float = self._base_value

    def read(self, step: int = 0) -> float:
        """Return a randomly drifted value around the configured base."""
        self._current = self._base_value + random.uniform(
            -self._drift_range, self._drift_range
        )
        return round(self._current, 2)

    def update(self, value: Any) -> None:
        """Override the base value."""
        self._base_value = float(value)
        self._cfg.value = value
