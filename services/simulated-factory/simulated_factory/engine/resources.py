"""Resource manager: owns sensors, dobot state, inventory cache, and physical resources."""

from __future__ import annotations

import asyncio
import copy
import importlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import yaml
from fastapi.encoders import jsonable_encoder

from simulated_factory.models import (
    DobotRuntimeState,
    PresetDefinition,
    SensorConfig,
    SensorUpdateRequest,
)
from simulated_factory.sensors.base import BaseSensor
from simulated_factory.engine.runtime import PhysicalResources
from simulated_factory.utils import raw_color_from_name, rgb_bytes_from_raw

if TYPE_CHECKING:
    from simulated_factory.events import EventStore

logger = logging.getLogger(__name__)

# Sensor type inference: map sensor-id prefix → plugin type name
_TYPE_INFERENCE_RULES: list[tuple[str, str]] = [
    ("color-", "color"),
    ("ir-", "ir"),
    ("distance-", "distance"),
]


class ResourceManager:
    """Owns sensor lifecycle, dobot state reads, and inventory polling."""

    def __init__(
        self,
        *,
        resources: PhysicalResources,
        event_store: EventStore,
        config_path: str,
        inventory_url: str | None = None,
    ):
        self._resources = resources
        self._event_store = event_store
        self._config_path = Path(config_path)
        self._inventory_url = (
            inventory_url
            if inventory_url is not None
            else os.getenv("INVENTORY_URL", "http://localhost:8103")
        )
        self._load_config()

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        payload = (
            yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
        )
        defaults = payload.get("defaults", {}).get("sensors", {})
        presets = payload.get("presets", {})

        self._resources.default_sensors = {
            sensor_id: self._make_plugin(sensor_id, config)
            for sensor_id, config in defaults.items()
        }

        self._presets_raw = presets
        self._resources.sensors = self._sensor_map_for_preset(None)

    def get_presets(self) -> dict[str, PresetDefinition]:
        """Parse preset definitions from config."""
        return {
            name: PresetDefinition(
                name=name,
                description=config.get("description", ""),
                sensor_overrides=config.get("sensor_overrides", {}),
                steps=config.get("steps", []),
            )
            for name, config in self._presets_raw.items()
        }

    # ------------------------------------------------------------------
    # Sensor map management
    # ------------------------------------------------------------------

    def sensor_map_for_preset(
        self, preset: PresetDefinition | None
    ) -> dict[str, BaseSensor]:
        return self._sensor_map_for_preset(preset)

    def _sensor_map_for_preset(
        self, preset: PresetDefinition | None
    ) -> dict[str, BaseSensor]:
        sensors: dict[str, BaseSensor] = {}

        for sensor_id, plugin in self._resources.default_sensors.items():
            if hasattr(plugin, "clone"):
                try:
                    sensors[sensor_id] = plugin.clone()
                    continue
                except Exception:
                    pass
            cfg = getattr(plugin, "_cfg", None)
            try:
                if cfg is not None and hasattr(cfg, "model_copy"):
                    cfg_copy = cfg.model_copy(deep=True)
                else:
                    cfg_copy = copy.deepcopy(cfg)
                sensors[sensor_id] = plugin.__class__(sensor_id, cfg_copy)
            except Exception:
                sensors[sensor_id] = plugin

        if preset is None:
            return sensors

        for sensor_id, override in preset.sensor_overrides.items():
            if sensor_id not in sensors:
                sensors[sensor_id] = self._make_plugin(sensor_id, {})
            plugin = sensors[sensor_id]
            if hasattr(plugin, "apply_overrides"):
                plugin.apply_overrides(override)
            else:
                override_filtered = {
                    k: v for k, v in override.items() if k != "type"
                }
                cfg = getattr(plugin, "_cfg", None)
                if cfg is not None and hasattr(cfg, "model_copy"):
                    try:
                        plugin._cfg = cfg.model_copy(update=override_filtered)
                    except Exception:
                        for k, v in override_filtered.items():
                            try:
                                setattr(plugin._cfg, k, v)
                            except Exception:
                                setattr(plugin, k, v)
                else:
                    for k, v in override_filtered.items():
                        setattr(plugin, k, v)

        return sensors

    # ------------------------------------------------------------------
    # Sensor plugin instantiation
    # ------------------------------------------------------------------

    def _make_plugin(self, sensor_id: str, config: dict[str, Any]) -> BaseSensor:
        sensor_type = self._infer_sensor_type(sensor_id, config)
        module_name = f"simulated_factory.sensors.{sensor_type.replace('-', '_')}"
        class_name = (
            "".join(
                w.capitalize()
                for w in sensor_type.replace("-", "_").split("_")
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

        try:
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
            return cls(sensor_id, cfg_obj)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to instantiate sensor plugin '{class_name}' for "
                f"sensor '{sensor_id}': {exc}"
            ) from exc

    def _infer_sensor_type(self, sensor_id: str, config: dict[str, Any]) -> str:
        """Infer the plugin type from config or sensor-id prefix.

        Supports explicit `type` field (preferred) and prefix-based inference
        for backward compatibility.
        """
        if config.get("type"):
            return str(config["type"])
        for prefix, sensor_type in _TYPE_INFERENCE_RULES:
            if sensor_id.startswith(prefix):
                return sensor_type
        return "generic"

    def make_plugin(self, sensor_id: str, config: dict[str, Any]) -> BaseSensor:
        """Public access to plugin instantiation."""
        return self._make_plugin(sensor_id, config)

    # ------------------------------------------------------------------
    # Sensor reads and updates
    # ------------------------------------------------------------------

    def get_sensor_configs(self) -> list[SensorConfig]:
        configs: list[SensorConfig] = []
        for key in sorted(self._resources.sensors.keys()):
            plugin = self._resources.sensors[key]
            to_cfg = getattr(plugin, "to_sensor_config", None)
            if callable(to_cfg):
                configs.append(to_cfg())
            else:
                cfg = getattr(plugin, "_cfg", None)
                if cfg is not None and hasattr(cfg, "model_copy"):
                    configs.append(cfg.model_copy(deep=True))
                else:
                    configs.append(cfg)  # type: ignore[arg-type]
        return configs

    async def update_sensor(
        self, sensor_id: str, update: SensorUpdateRequest
    ) -> SensorConfig:
        if sensor_id not in self._resources.sensors:
            self._resources.sensors[sensor_id] = self._make_plugin(sensor_id, {})
        plugin = self._resources.sensors[sensor_id]
        update_dict = update.model_dump(exclude_none=True)

        if hasattr(plugin, "apply_update_request"):
            plugin.apply_update_request(update_dict)
        else:
            if "value" in update_dict:
                try:
                    plugin.update(update_dict["value"])
                except Exception:
                    pass
            other = {
                k: v for k, v in update_dict.items() if k not in ("value", "mode")
            }
            if other:
                cfg = getattr(plugin, "_cfg", None)
                if cfg is not None and hasattr(cfg, "model_copy"):
                    try:
                        plugin._cfg = cfg.model_copy(update=other)
                    except Exception:
                        for k, v in other.items():
                            try:
                                setattr(plugin._cfg, k, v)
                            except Exception:
                                setattr(plugin, k, v)
                else:
                    for k, v in other.items():
                        setattr(plugin, k, v)

        await self._event_store.append(
            "STATE",
            message=f"Sensor {sensor_id} updated",
            payload={
                "sensorId": sensor_id,
                "config": jsonable_encoder(
                    plugin.to_dict()
                    if hasattr(plugin, "to_dict")
                    else getattr(plugin, "_cfg", None)
                ),
            },
        )

        if hasattr(plugin, "to_sensor_config"):
            return plugin.to_sensor_config()
        cfg = getattr(plugin, "_cfg", None)
        if cfg is not None and hasattr(cfg, "model_copy"):
            return cfg.model_copy(deep=True)
        return cfg  # type: ignore[return-value]

    def _sensor_for(self, robot_name: str, prefix: str) -> BaseSensor:
        sensor_id = f"{prefix}-{robot_name}"
        if sensor_id not in self._resources.sensors:
            self._resources.sensors[sensor_id] = self._make_plugin(sensor_id, {})
        return self._resources.sensors[sensor_id]

    def read_color(self, robot_name: str) -> tuple[str, list[int]]:
        plugin = self._sensor_for(robot_name, "color")
        try:
            return plugin.read(self._current_step_getter())  # type: ignore[return-value]
        except TypeError:
            return plugin.read()  # type: ignore[return-value]

    def read_ir(self, robot_name: str) -> bool:
        plugin = self._sensor_for(robot_name, "ir")
        try:
            return plugin.read(self._current_step_getter())  # type: ignore[return-value]
        except TypeError:
            return plugin.read()  # type: ignore[return-value]

    def read_color_sensor_bytes(self) -> dict[str, int]:
        color, raw_color = self.read_color("left")
        rgb = rgb_bytes_from_raw(raw_color or raw_color_from_name(color))
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    def set_current_step_getter(self, getter) -> None:
        """Set a callable that returns the current step index."""
        self._current_step_getter = getter

    # ------------------------------------------------------------------
    # Dobot state
    # ------------------------------------------------------------------

    def get_dobot_state(self, robot_name: str) -> DobotRuntimeState:
        return self._resources.dobots.setdefault(
            robot_name, DobotRuntimeState()
        ).model_copy(deep=True)

    # ------------------------------------------------------------------
    # Inventory polling
    # ------------------------------------------------------------------

    def get_inventory_cache(self) -> dict:
        if self._resources.inventory_cache is None:
            return {"grid": None, "rows": 0, "cols": 0}
        return self._resources.inventory_cache

    def start_inventory_poller(self) -> None:
        if (
            self._resources.inventory_poll_task is not None
            and not self._resources.inventory_poll_task.done()
        ):
            return
        self._resources.inventory_poll_task = asyncio.create_task(
            self._inventory_poll_loop()
        )

    async def stop_inventory_poller(self) -> None:
        task = self._resources.inventory_poll_task
        self._resources.inventory_poll_task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    async def _inventory_poll_loop(self) -> None:
        url = self._inventory_url.rstrip("/") + "/inventory"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                while True:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            self._resources.inventory_cache = response.json()
                    except Exception:
                        pass
                    await asyncio.sleep(3.0)
        except asyncio.CancelledError:
            raise
