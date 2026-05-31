from __future__ import annotations

from simulated_factory.actuators.base import BaseActuator
from simulated_factory.actuators.dobot import DobotActuator

_ROBOT_NAMES: tuple[str, ...] = ("left", "right")


class ActuatorRegistry:
    """Holder for actuator plugins.

    Unlike :class:`SensorRegistry`, there is no config-driven discovery: the
    known dobot actuators are instantiated directly. Mirrors
    ``SensorRegistry.sensors()`` by dispensing fresh instances on each call,
    so the engine can rebuild its working set without aliasing the previous
    one.
    """

    def actuators(self) -> dict[str, BaseActuator]:
        return {name: DobotActuator(name) for name in _ROBOT_NAMES}
