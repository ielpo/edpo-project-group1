from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml

from simulated_factory.models import PresetDefinition, SensorConfig
from simulated_factory.sensors.base import BaseSensor

_TYPE_INFERENCE_RULES: list[tuple[str, str]] = [
    ("color-", "color"),
    ("ir-", "ir"),
    ("distance-", "distance"),
]


class SensorRegistry:
    def __init__(self, config_path: str):
        payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        defaults = payload.get("defaults", {}).get("sensors", {})

        self._defaults: dict[str, BaseSensor] = {
            sensor_id: self.make(sensor_id, cfg) for sensor_id, cfg in defaults.items()
        }
        self._presets_raw: dict[str, dict[str, Any]] = payload.get("presets", {})

    def get_presets(self) -> dict[str, PresetDefinition]:
        return {
            name: PresetDefinition(
                name=name,
                description=config.get("description", ""),
                steps=config.get("steps", []),
            )
            for name, config in self._presets_raw.items()
        }

    def sensors(self) -> dict[str, BaseSensor]:
        return {
            sensor_id: plugin.clone() for sensor_id, plugin in self._defaults.items()
        }

    def make(self, sensor_id: str, config: dict[str, Any] | SensorConfig) -> BaseSensor:
        sensor_type = self._infer_sensor_type(sensor_id, config)
        module_name = f"simulated_factory.sensors.{sensor_type.replace('-', '_')}"
        class_name = (
            "".join(
                word.capitalize() for word in sensor_type.replace("-", "_").split("_")
            )
            + "Sensor"
        )

        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                f"Sensor plugin for '{sensor_id}' (type='{sensor_type}') not found. "
                f"Expected module '{module_name}'. Original error: {exc}"
            ) from exc

        try:
            cls = getattr(module, class_name)
        except AttributeError as exc:
            raise RuntimeError(
                f"Sensor plugin module '{module_name}' does not define class "
                f"'{class_name}'. Sensor: '{sensor_id}' (type='{sensor_type}')."
            ) from exc

        if isinstance(config, SensorConfig):
            cfg_obj = config
        else:
            cfg_dict = dict(config or {})
            cfg_dict.setdefault("name", sensor_id)
            cfg_dict.setdefault("type", sensor_type)
            config_cls = getattr(module, class_name + "Config", None)
            if config_cls is None:
                cfg_obj = SensorConfig(**cfg_dict)
            else:
                try:
                    cfg_obj = config_cls(**cfg_dict)
                except Exception:
                    cfg_obj = SensorConfig(**cfg_dict)

        try:
            return cls(sensor_id, cfg_obj)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to instantiate sensor plugin '{class_name}' for "
                f"sensor '{sensor_id}': {exc}"
            ) from exc

    def _infer_sensor_type(
        self, sensor_id: str, config: dict[str, Any] | SensorConfig
    ) -> str:
        explicit_type: str | None = None
        if isinstance(config, SensorConfig):
            explicit_type = config.type or None
        elif config.get("type"):
            explicit_type = str(config["type"])

        if explicit_type:
            return explicit_type

        for prefix, sensor_type in _TYPE_INFERENCE_RULES:
            if sensor_id.startswith(prefix):
                return sensor_type

        return "generic"
