"""Color sensor plugin — supports fixed and scripted modes."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from simulated_factory.models import SensorConfig
from simulated_factory.sensors.base import BaseSensor
from simulated_factory.utils import raw_color_from_name


class ColorSensorConfig(SensorConfig):
    mode: str = "fixed"
    value: str | None = None
    raw_color: list[int] = Field(default_factory=list)
    scripted_values: list[Any] = Field(default_factory=list)
    sensorId: str = ""


class ColorSensor(BaseSensor):
    """Sensor plugin for color detection (left/right dobot color sensors)."""

    def __init__(self, name: str, config: Any) -> None:
        if isinstance(config, dict):
            cfg_dict = dict(config)
            cfg_dict.setdefault("name", name)
            cfg_dict.setdefault("type", "color")
            cfg_dict.setdefault("sensorId", name)
            cfg = ColorSensorConfig(**cfg_dict)
        elif isinstance(config, ColorSensorConfig):
            cfg = config
        else:
            cfg = config  # type: ignore[assignment]
        super().__init__(name, cfg)
        self._cfg: ColorSensorConfig  # type: ignore[assignment]
        if not self._cfg.sensorId:
            self._cfg.sensorId = name

    def read(self, step: int | None = None) -> tuple[str, list[int]]:
        cfg = self._cfg
        if cfg.mode == "scripted" and cfg.scripted_values and step is not None:
            idx = max(0, min(step - 1, len(cfg.scripted_values) - 1))
            if step == 0:
                idx = 0
            color = str(cfg.scripted_values[idx]).upper()
            return color, raw_color_from_name(color)
        color = str(cfg.value or "YELLOW").upper()
        raw = cfg.raw_color if cfg.raw_color else raw_color_from_name(color)
        return color, raw

    def update(self, value: Any) -> None:
        self._cfg.value = str(value).upper()
        self._cfg.raw_color = raw_color_from_name(str(value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "mode": self._cfg.mode,
            "value": self._cfg.value,
            "raw_color": self._cfg.raw_color,
            "scripted_values": self._cfg.scripted_values,
        }

    def to_sensor_config(self) -> ColorSensorConfig:
        return self._cfg.model_copy(deep=True)

    def clone(self) -> "ColorSensor":
        return ColorSensor(self.name, self._cfg.model_copy(deep=True))

    def apply_update_request(self, update: dict[str, Any]) -> None:
        if "value" in update:
            self._cfg.value = update["value"]
        if "raw_color" in update:
            self._cfg.raw_color = update["raw_color"]
        if "mode" in update:
            self._cfg.mode = update["mode"]
        if "scripted_values" in update:
            self._cfg.scripted_values = update["scripted_values"]

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        filtered = {k: v for k, v in overrides.items() if k != "type"}
        for k, v in filtered.items():
            if hasattr(self._cfg, k):
                setattr(self._cfg, k, v)

    @property
    def value(self) -> str | None:
        return self._cfg.value

    @value.setter
    def value(self, val: str | None) -> None:
        self._cfg.value = val
