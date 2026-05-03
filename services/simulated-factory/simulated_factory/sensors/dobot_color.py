from typing import cast

from simulated_factory.sensors.base import BaseSensor
from simulated_factory.models import SensorConfig
from simulated_factory.utils import raw_color_from_name


class DobotColorSensorConfig(SensorConfig):
    color: str
    raw_color: list[int]

class DobotColorSensor(BaseSensor):
    """Dobot sensor for color detection."""

    def read(self) -> tuple[str, list[int]]:
        cfg = cast(DobotColorSensorConfig, self._cfg)
        color = str(cfg.color or "YELLOW").upper()
        raw_color = cfg.raw_color or raw_color_from_name(color)
        return color, raw_color

    def update(self, value: str) -> None:
        cfg = cast(DobotColorSensorConfig, self._cfg)
        cfg.raw_color = raw_color_from_name(value)
        cfg.color = value
