"""Color sensor plugin — manual value with preset-driven updates."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from pydantic import Field

from simulated_factory.models import SensorConfig
from simulated_factory.sensors.base import BaseSensor, MqttSensor
from simulated_factory.utils import raw_color_from_name, rgb_bytes_from_raw


class ColorSensorConfig(SensorConfig):
    value: str | None = None
    raw_color: list[int] = Field(default_factory=list)
    sensorId: str = ""
    mqtt_topic: str = "DobotFactory/ColorSensor"
    cadence_ms: int = 1000
    message_id: int = 0


class ColorSensor(BaseSensor, MqttSensor):
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
        self._message_id = self._cfg.message_id

    def read(self) -> tuple[str, list[int]]:
        cfg = self._cfg
        color = str(cfg.value or "YELLOW").upper()
        raw = cfg.raw_color if cfg.raw_color else raw_color_from_name(color)
        return color, raw

    def read_rgb_bytes(self) -> dict[str, int]:
        """Return the current color as an RGB byte dict suitable for sensor API responses."""
        color, raw_color = self.read()
        rgb = rgb_bytes_from_raw(raw_color or raw_color_from_name(color))
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    def update(self, value: Any) -> None:
        self._cfg.value = str(value).upper()
        self._cfg.raw_color = raw_color_from_name(str(value))

    def mqtt_message(self) -> tuple[str, str] | None:
        color, raw_color = self.read()
        rgb = rgb_bytes_from_raw(raw_color or raw_color_from_name(color))
        message = {
            "type": self._cfg.type,
            "sensorId": self._cfg.sensorId,
            "messageID": self._message_id,
            "r": rgb[0],
            "g": rgb[1],
            "b": rgb[2],
        }
        self._message_id += 1
        return self._cfg.mqtt_topic, json.dumps(message)

    async def start_task(self) -> None:
        interval = self._cfg.cadence_ms / 1000.0
        self._publish_task: asyncio.Task[None] = asyncio.create_task(
            self._publish_loop(interval)
        )

    async def stop_task(self) -> None:
        task = getattr(self, "_publish_task", None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._publish_task = None

    async def _publish_loop(self, interval: float) -> None:
        try:
            while True:
                if getattr(self, "_active", True):
                    await self.publish()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "value": self._cfg.value,
            "raw_color": self._cfg.raw_color,
            "mqtt_topic": self._cfg.mqtt_topic,
            "cadence_ms": self._cfg.cadence_ms,
        }
