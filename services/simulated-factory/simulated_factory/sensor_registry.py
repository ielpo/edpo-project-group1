from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml

from simulated_factory.models import PresetDefinition, SensorConfig
from simulated_factory.sensors.base import BaseSensor, MqttSensor

_TYPE_INFERENCE_RULES: list[tuple[str, str]] = [
    ("color-", "color"),
    ("ir-", "ir"),
    ("distance-", "distance"),
]


class SensorRegistry:
    def __init__(self, config_path: str, mqtt_publisher: Any = None):
        self._mqtt_publisher = mqtt_publisher

        payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        defaults = payload.get("defaults", {}).get("sensors", {})

        self._defaults: dict[str, BaseSensor] = {
            sensor_id: self.make(sensor_id, cfg) for sensor_id, cfg in defaults.items()
        }
        self._presets_raw: dict[str, dict[str, Any]] = payload.get("presets", {})
        self._live: dict[str, BaseSensor] = {}
        self.reset()

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

    # ------------------------------------------------------------------
    # Live pool lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Rebuild the live pool from defaults (clone + wire)."""
        self._live = {}
        for sensor_id, plugin in self._defaults.items():
            sensor = plugin.clone()
            if isinstance(sensor, MqttSensor) and self._mqtt_publisher is not None:
                sensor.wire(self._mqtt_publisher)
            self._live[sensor_id] = sensor

    def get_or_create(self, sensor_id: str) -> BaseSensor:
        """Return existing live sensor or create, wire, and register a new one."""
        if sensor_id in self._live:
            return self._live[sensor_id]
        sensor = self.make(sensor_id, {})
        if isinstance(sensor, MqttSensor) and self._mqtt_publisher is not None:
            sensor.wire(self._mqtt_publisher)
        self._live[sensor_id] = sensor
        return sensor

    async def activate(self) -> None:
        """Start background tasks for all MQTT sensors in the live pool."""
        for sensor in self._live.values():
            if isinstance(sensor, MqttSensor):
                await sensor.start_task()

    async def deactivate(self) -> None:
        """Stop background tasks for all MQTT sensors in the live pool."""
        for sensor in self._live.values():
            if isinstance(sensor, MqttSensor):
                await sensor.stop_task()

    def pause(self) -> None:
        """Pause publishing for all MQTT sensors."""
        for sensor in self._live.values():
            if isinstance(sensor, MqttSensor):
                sensor.pause_task()

    def resume(self) -> None:
        """Resume publishing for all MQTT sensors."""
        for sensor in self._live.values():
            if isinstance(sensor, MqttSensor):
                sensor.resume_task()

    def apply_updates(self, updates: dict[str, Any]) -> None:
        """Apply sensor value changes from a preset step."""
        for sensor_id, value in updates.items():
            sensor = self.get_or_create(sensor_id)
            sensor.update(value)

    def configs(self) -> list[SensorConfig]:
        """Return configs for all live sensors."""
        return [
            self._live[sensor_id].to_config()
            for sensor_id in sorted(self._live.keys())
        ]

    def apply_sensor_update(self, sensor_id: str, update: dict[str, Any]) -> SensorConfig:
        """Apply an individual sensor update (from API) and return updated config."""
        sensor = self.get_or_create(sensor_id)
        sensor.apply_update(update)
        return sensor.to_config()

    @property
    def live(self) -> dict[str, BaseSensor]:
        """Read-only access to the live sensor pool."""
        return self._live

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
