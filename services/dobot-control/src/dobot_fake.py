import logging
from enum import Enum, auto
from pydobotplus import CustomPosition

from commands import (
    Command,
    RunConveyorCommand,
    MoveConveyorCommand,
    MovementCommand,
    RelativeMovementCommand,
    MovementSpeedCommand,
    SuctionCupCommand,
)


class Status(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    PAUSED = auto()


class DobotFake:
    def __init__(self, name: str):
        self.logger = logging.getLogger(__name__)

        self.speed: float = 0.0
        self.acceleration: float = 100.0
        self.status: Status = Status.INACTIVE
        self.position = CustomPosition(0.0, 0.0, 0.0, 0.0)
        self.suction_enabled = False
        self.conveyor_speed: float = 0.0
        self.conveyor_distance: float = 0.0
        self.conveyor_direction = None
        self.color_raw: list[int] = [0, 0, 0]
        self.ir_reading: bool = True

        self.name = name

        self.set_speed(50.0)
        self.logger.info("[%s] Fake Dobot initialized", self.name)

    def home(self):
        """Home the Dobot"""
        self.position = CustomPosition(0.0, 0.0, 0.0, 0.0)
        self.status = Status.INACTIVE
        self.logger.info("[%s] HOME -> position=%s", self.name, self.position)

    def execute_dobot_commands(self, commands: list[Command]):
        """
        Execute a series of movement commands on the Dobot.
        """
        self.status = Status.ACTIVE
        for command in commands:
            try:
                self.logger.info("[%s] EXECUTE -> %s", self.name, command)
                match command:
                    case MovementCommand():
                        self.logger.info(
                            "[%s] MOVE ABSOLUTE -> mode=%s position=%s",
                            self.name,
                            command.mode.name,
                            (command.x, command.y, command.z, command.r),
                        )
                        self.position = CustomPosition(
                            command.x, command.y, command.z, command.r
                        )
                    case RelativeMovementCommand():
                        self.logger.info(
                            "[%s] MOVE RELATIVE -> position=%s",
                            self.name,
                            (command.x, command.y, command.z, command.r),
                        )
                        if command.x:
                            self.position.x += command.x
                        if command.y:
                            self.position.y += command.y
                        if command.z:
                            self.position.z += command.z
                        if command.r:
                            self.position.r += command.r
                    case MovementSpeedCommand():
                        self.set_speed(command.speed, command.acceleration)
                    case SuctionCupCommand():
                        self.suction_enabled = command.suck
                        self.logger.info(
                            "[%s] SUCTION -> enabled=%s",
                            self.name,
                            self.suction_enabled,
                        )
                    case RunConveyorCommand():
                        self.run_conveyor(command)
                    case MoveConveyorCommand():
                        self.move_conveyor(command)
                    case _:
                        self.logger.warning(
                            "[%s] Unsupported fake command ignored: %s",
                            self.name,
                            type(command).__name__,
                        )

            except Exception as e:
                self.logger.error(f"Error executing command: {e}")

        self.logger.info(
            "[%s] Final position -> %s",
            self.name,
            (self.position.x, self.position.y, self.position.z, self.position.r),
        )
        self.status = Status.INACTIVE

    def stop_robot(self) -> None:
        self.logger.info("[%s] STOP", self.name)
        self.set_speed(0, 0)

    def set_speed(self, speed: float, acceleration: float | None = None) -> None:
        self.speed = speed
        if acceleration is not None:
            self.acceleration = acceleration
            self.logger.info(
                "[%s] SPEED -> speed=%s acceleration=%s",
                self.name,
                self.speed,
                self.acceleration,
            )
        else:
            self.logger.info("[%s] SPEED -> speed=%s", self.name, self.speed)

    def move_conveyor(self, command: MoveConveyorCommand):
        self.conveyor_speed = command.speed
        self.conveyor_distance = command.distance
        self.conveyor_direction = command.direction
        self.logger.info(
            "[%s] CONVEYOR MOVE -> speed=%s distance=%s direction=%s",
            self.name,
            command.speed,
            command.distance,
            command.direction.name,
        )

    def run_conveyor(self, command: RunConveyorCommand):
        self.conveyor_speed = command.speed
        self.conveyor_direction = command.direction
        self.logger.info(
            "[%s] CONVEYOR RUN -> speed=%s direction=%s",
            self.name,
            command.speed,
            command.direction.name,
        )

    def read_color(self) -> tuple[str, list[int]]:
        color_raw = self.color_raw
        if color_raw[0] == 1:
            color = "RED"
        elif color_raw[1] == 1:
            color = "GREEN"
        elif color_raw[2] == 1:
            color = "BLUE"
        else:
            color = "YELLOW"

        self.logger.info(
            "[%s] READ COLOR -> color=%s raw=%s", self.name, color, color_raw
        )
        return color, color_raw

    def read_ir(self) -> bool:
        self.logger.info("[%s] READ IR -> %s", self.name, self.ir_reading)
        return self.ir_reading
