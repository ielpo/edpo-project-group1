from typing import Dict

from pydantic import BaseModel


class RobotConfig(BaseModel):
    robot_port: str
    server_port: int


class SimulatorConfig(BaseModel):
    url: str | None = None
    broker: str | None = None
    command_timeout_seconds: float = 1.0
    sensor_timeout_seconds: float = 1.0


class Config(BaseModel):
    robots: Dict[str, RobotConfig]
    default_robot: str
    simulator: SimulatorConfig | None = None
