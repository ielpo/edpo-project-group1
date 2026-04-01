import logging
import pydobotplus
from enum import Enum, auto

from commands import (
    Command,
    MovementCommand,
    MovementSpeedCommand,
    SuctionCupCommand,
    RelativeMovementCommand,
    MoveConveyorCommand,
    RunConveyorCommand,
)


class Status(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    PAUSED = auto()


class Dobot:
    def __init__(self, name: str, port: str):
        self.speed: float = 0.0
        self.acceleration: float = 100.0
        self.status: Status = Status.INACTIVE

        self.name = name
        self.port = port

        self.device = pydobotplus.Dobot(port=self.port)

        self.set_speed(50.0)
        self.device.suck(False)

        self.logger = logging.Logger(__name__)

    def home(self):
        """Home the Dobot"""
        self.device.home()

    def execute_dobot_commands(self, commands: list[Command]):
        """
        Execute a series of commands on the Dobot.
        """
        self.status = Status.ACTIVE
        for command in commands:
            try:
                match command:
                    case MovementCommand():
                        self.device.move_to(
                            command.x,
                            command.y,
                            command.z,
                            command.r,
                            mode=command.mode.value,
                        )
                    case RelativeMovementCommand():
                        self.device.move_rel(command.x, command.y, command.z, command.r)
                    case MovementSpeedCommand():
                        self.set_speed(command.speed, command.acceleration)
                    case SuctionCupCommand():
                        self.device.suck(command.suck)
                    case MoveConveyorCommand():
                        self.device.conveyor_belt_distance(
                            command.speed, command.distance, command.direction
                        )
                    case RunConveyorCommand():
                        self.device.conveyor_belt(command.speed, command.direction)

            except Exception as e:
                self.logger.error(f"Error executing command: {e}")

    def stop_robot(self) -> None:
        self.set_speed(0, 0)

    def set_speed(self, speed: float, acceleration: float | None = None) -> None:
        self.speed = speed
        if acceleration:
            self.device.speed(speed, acceleration)
            self.acceleration = acceleration
        else:
            self.device.speed(speed)

    def read_color(self) -> tuple[str, list[int]]:
        color_raw: list[int] = self.device.get_color()
        if color_raw[0] == 1:
            color = "RED"
        elif color_raw[1] == 1:
            color = "GREEN"
        elif color_raw[2] == 1:
            color = "BLUE"
        else:
            color = "YELLOW"

        return color, color_raw

    def read_ir(self) -> bool:
        self.device.set_ir(enable=True)
        reading = bool(self.device.get_ir())
        self.device.set_ir(enable=False)
        return reading
