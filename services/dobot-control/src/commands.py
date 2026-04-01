from enum import Enum, auto
from pydantic import BaseModel
from pydobotplus.dobotplus import MODE_PTP


class Mode(Enum):
    MOVE_LINEAR = MODE_PTP.MOVL_XYZ
    MOVE_JOINT = MODE_PTP.MOVJ_XYZ
    JUMP = MODE_PTP.JUMP_MOVL_XYZ


class Direction(Enum):
    FORWARD = 1
    STOP = 0
    REVERSE = -1


class GripperState(Enum):
    OPEN = auto()
    CLOSE = auto()
    DISABLE = auto()


Command = BaseModel


class MovementCommand(Command):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    r: float = 0.0
    mode: Mode = Mode.MOVE_JOINT


class RelativeMovementCommand(Command):
    x: float | None = None
    y: float | None = None
    z: float | None = None
    r: float | None = None


class MoveConveyorCommand(Command):
    direction: Direction = Direction.STOP
    speed: float = 0.0
    distance: float = 0.0


class RunConveyorCommand(Command):
    direction: Direction = Direction.STOP
    speed: float = 0.0


class SuctionCupCommand(Command):
    suck: bool = False


class GripperCommand(Command):
    state: GripperState = GripperState.DISABLE


class MovementSpeedCommand(BaseModel):
    speed: float = 0.0
    acceleration: float | None = None


command_type_map = {
    "MovementCommand": MovementCommand,
    "RelativeMovementCommand": RelativeMovementCommand,
    "RunConveyorCommand": RunConveyorCommand,
    "MoveConveyorCommand": MoveConveyorCommand,
    "SuctionCupCommand": SuctionCupCommand,
    "GripperCommand": GripperCommand,
    "MovementSpeedCommand": MovementSpeedCommand,
}
