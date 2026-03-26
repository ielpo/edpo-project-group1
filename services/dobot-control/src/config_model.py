from typing import Dict

from pydantic import BaseModel


class RobotConfig(BaseModel):
    robot_port: str
    server_port: int


class Config(BaseModel):
    robots: Dict[str, RobotConfig]
    default_robot: str
