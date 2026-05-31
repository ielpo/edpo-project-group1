from __future__ import annotations

import logging
from typing import Any

from simulated_factory.actuators.base import BaseActuator
from simulated_factory.models import DobotRuntimeState, Position

logger = logging.getLogger(__name__)


class DobotActuator(BaseActuator):
    """Actuator plugin for dobot robots.

    Owns a :class:`DobotRuntimeState` and applies the simulator command set to
    it. The command logic is a direct extraction of the engine's former
    ``_apply_dobot_commands`` match/case.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._state = DobotRuntimeState()

    def apply(self, commands: list[dict]) -> None:
        for command in commands:
            command_type = str(command.get("type", "unknown"))
            match command_type:
                case "move":
                    target = command.get("target", {})
                    self._state.position = Position(
                        x=float(target.get("x", self._state.position.x)),
                        y=float(target.get("y", self._state.position.y)),
                        z=float(target.get("z", self._state.position.z)),
                        r=float(target.get("r", self._state.position.r)),
                    )
                case "move-relative":
                    offset = command.get("offset", {})
                    self._state.position.x += float(offset.get("x", 0.0) or 0.0)
                    self._state.position.y += float(offset.get("y", 0.0) or 0.0)
                    self._state.position.z += float(offset.get("z", 0.0) or 0.0)
                    self._state.position.r += float(offset.get("r", 0.0) or 0.0)
                case "set-speed":
                    self._state.speed = float(
                        command.get("speed", self._state.speed)
                    )
                    if command.get("acceleration") is not None:
                        self._state.acceleration = float(command["acceleration"])
                case "suction-cup":
                    self._state.suction_enabled = bool(command.get("enabled", False))
                case "run-conveyor":
                    self._state.conveyor_speed = float(command.get("speed", 0.0))
                    self._state.conveyor_direction = str(
                        command.get("direction", "STOP")
                    )
                case "move-conveyor":
                    self._state.conveyor_speed = float(command.get("speed", 0.0))
                    self._state.conveyor_distance = float(
                        command.get("distance", 0.0)
                    )
                    self._state.conveyor_direction = str(
                        command.get("direction", "STOP")
                    )
                case _:
                    logger.warning(
                        "Ignoring unsupported simulator command type %s",
                        command_type,
                    )
            self._state.last_command = command_type

    def state(self) -> Any:
        return self._state.model_copy(deep=True)
