import logging
from typing import Any

import httpx

from commands import (
    Command,
    Mode,
    Direction,
    MoveConveyorCommand,
    MovementCommand,
    MovementSpeedCommand,
    RelativeMovementCommand,
    RunConveyorCommand,
    SuctionCupCommand,
)


class SimulatorClient:
    def __init__(
        self,
        base_url: str,
        sensor_timeout_seconds: float,
        command_timeout_seconds: float,
        logger: logging.Logger,
    ):
        self.base_url = base_url.rstrip("/")
        self.sensor_timeout_seconds = sensor_timeout_seconds
        self.command_timeout_seconds = command_timeout_seconds
        self.logger = logger

    def forward_command(self, robot_name: str, command: Command) -> None:
        try:
            response = httpx.post(
                f"{self.base_url}/api/dobot/{robot_name}/commands",
                json=self._serialize_command(command),
                timeout=self.command_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self.logger.warning(
                "[%s] Failed to forward command to simulator %s: %s",
                robot_name,
                self.base_url,
                exc,
            )

    def read_color(self, robot_name: str) -> tuple[str, list[int]] | None:
        try:
            response = httpx.get(
                f"{self.base_url}/api/dobot/{robot_name}/color",
                timeout=self.sensor_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self.logger.warning(
                "[%s] Failed to read color from simulator %s: %s",
                robot_name,
                self.base_url,
                exc,
            )
            return None

        payload = response.json()
        color = str(payload.get("color", "YELLOW"))
        raw_color = payload.get("raw_color", [0, 0, 0])
        return color, [int(value) for value in raw_color]

    def read_ir(self, robot_name: str) -> bool | None:
        try:
            response = httpx.get(
                f"{self.base_url}/api/dobot/{robot_name}/ir",
                timeout=self.sensor_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self.logger.warning(
                "[%s] Failed to read IR from simulator %s: %s",
                robot_name,
                self.base_url,
                exc,
            )
            return None

        payload = response.json()
        return bool(payload.get("ir", True))

    def _serialize_command(self, command: Command) -> dict[str, Any]:
        payload: dict[str, Any]
        if isinstance(command, MovementCommand):
            payload = {
                "type": "move",
                "target": {
                    "x": command.x,
                    "y": command.y,
                    "z": command.z,
                    "r": command.r,
                },
                "mode": self._enum_name(command.mode),
            }
        elif isinstance(command, RelativeMovementCommand):
            payload = {
                "type": "move-relative",
                "offset": {
                    "x": command.x,
                    "y": command.y,
                    "z": command.z,
                    "r": command.r,
                },
            }
        elif isinstance(command, MovementSpeedCommand):
            payload = {
                "type": "set-speed",
                "speed": command.speed,
                "acceleration": command.acceleration,
            }
        elif isinstance(command, SuctionCupCommand):
            payload = {"type": "suction-cup", "enabled": command.suck}
        elif isinstance(command, RunConveyorCommand):
            payload = {
                "type": "run-conveyor",
                "speed": command.speed,
                "direction": self._enum_name(command.direction),
            }
        elif isinstance(command, MoveConveyorCommand):
            payload = {
                "type": "move-conveyor",
                "speed": command.speed,
                "distance": command.distance,
                "direction": self._enum_name(command.direction),
            }
        else:
            payload = {"type": command.__class__.__name__, **command.model_dump()}

        return payload

    def _enum_name(self, value: Mode | Direction | None) -> str | None:
        if value is None:
            return None

        return value.name