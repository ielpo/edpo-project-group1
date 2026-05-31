from __future__ import annotations

from typing import Any

from simulated_factory.actuators.base import BaseActuator
from simulated_factory.actuators.dobot import DobotActuator
from simulated_factory.models import DobotRuntimeState

_ROBOT_NAMES: tuple[str, ...] = ("left", "right")


class ActuatorRegistry:
    """Sole live owner of dobot actuator state.

    Holds the live actuator instances and exposes command application,
    state queries, and reset without handing out the internal map.
    """

    def __init__(self) -> None:
        self._actuators: dict[str, BaseActuator] = {
            name: DobotActuator(name) for name in _ROBOT_NAMES
        }

    # ------------------------------------------------------------------
    # Command application
    # ------------------------------------------------------------------

    def apply_commands(self, robot_name: str, commands: list[dict]) -> None:
        """Apply a batch of commands to the named actuator."""
        self._actuators[robot_name].apply(commands)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self, robot_name: str) -> DobotRuntimeState:
        """Return a deep copy of one actuator's current state."""
        actuator = self._actuators.get(robot_name)
        if actuator is None:
            raise KeyError(robot_name)
        return actuator.state()

    def all_states(self) -> dict[str, DobotRuntimeState]:
        """Return deep copies of all actuator states keyed by name."""
        return {name: act.state() for name, act in self._actuators.items()}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Rebuild all actuators to their default state."""
        self._actuators = {name: DobotActuator(name) for name in _ROBOT_NAMES}

    # ------------------------------------------------------------------
    # Legacy compatibility (to be removed after full migration)
    # ------------------------------------------------------------------

    def actuators(self) -> dict[str, BaseActuator]:
        """Dispense fresh instances — legacy API kept during migration."""
        return {name: DobotActuator(name) for name in _ROBOT_NAMES}
