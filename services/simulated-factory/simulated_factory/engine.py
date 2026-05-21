import asyncio
import importlib
import logging
import os
import copy
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi.encoders import jsonable_encoder

from simulated_factory.adapters.mqtt_publisher import MqttPublisher
from simulated_factory.events import EventStore
from simulated_factory.models import (
    AwaitRequest,
    DobotRuntimeState,
    InteractiveConfig,
    PendingAction,
    Position,
    PresetDefinition,
    PresetStep,
    SensorConfig,
    SensorUpdateRequest,
    SimulationState,
    SimulationStatus,
    utc_now,
)
from simulated_factory.sensors.base import BaseSensor
from simulated_factory.utils import (
    path_pattern_to_regex,
    raw_color_from_name,
    rgb_bytes_from_raw,
)

# Sensor type inference: map sensor-id prefix → plugin type name
_TYPE_INFERENCE_RULES: list[tuple[str, str]] = [
    ("color-", "color"),
    ("ir-", "ir"),
    ("distance-", "distance"),
]


_DEFAULT_INTERCEPTED: frozenset[str] = frozenset(
    {
        "move",
        "move-relative",
        "set-speed",
        "suction-cup",
        "run-conveyor",
        "move-conveyor",
    }
)


class SimulationEngine:
    def __init__(
        self,
        *,
        config_path: str,
        event_store: EventStore,
        mqtt_publisher: MqttPublisher,
        inventory_url: str | None = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self.event_store = event_store
        self.mqtt_publisher = mqtt_publisher
        self._inventory_url = (
            inventory_url
            if inventory_url is not None
            else os.getenv("INVENTORY_URL", "http://localhost:8103")
        )
        self.state = SimulationState()
        self._default_sensors: dict[str, BaseSensor] = {}
        self.sensors: dict[str, BaseSensor] = {}
        self.presets: dict[str, PresetDefinition] = {}
        self._run_counter = 0
        self._stop_requested = False
        self._run_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self.interactive_config: InteractiveConfig = InteractiveConfig()
        self._pending: dict[str, PendingAction] = {}
        self._pending_counter = 0
        self._step_gate: tuple[AwaitRequest, asyncio.Event, PresetStep] | None = None
        self._inventory_cache: dict | None = None
        self._inventory_poll_task: asyncio.Task | None = None
        self._load_config()

    def _load_config(self) -> None:
        payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        defaults = payload.get("defaults", {}).get("sensors", {})
        presets = payload.get("presets", {})

        self._default_sensors = {
            sensor_id: self._make_plugin(sensor_id, config)
            for sensor_id, config in defaults.items()
        }
        self.presets = {
            name: PresetDefinition(
                name=name,
                description=config.get("description", ""),
                sensor_overrides=config.get("sensor_overrides", {}),
                steps=config.get("steps", []),
            )
            for name, config in presets.items()
        }
        self.sensors = self._sensor_map_for_preset(None)

    def get_dobot_state(self, robot_name: str) -> DobotRuntimeState:
        return self.state.dobots.setdefault(robot_name, DobotRuntimeState()).model_copy(
            deep=True
        )

    # ------------------------------------------------------------------
    # Preset handling
    # ------------------------------------------------------------------
    def list_presets(self) -> list[dict[str, object]]:
        return [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in self.presets.values()
        ]

    async def run_preset(self, preset_name: str) -> str:
        preset = self.presets.get(preset_name)
        if preset is None:
            raise KeyError(preset_name)

        async with self._lock:
            if self._run_task and not self._run_task.done():
                raise RuntimeError("simulation already running")

            self._run_counter += 1
            run_id = f"run-{self._run_counter:04d}"
            self._stop_requested = False
            self.sensors = self._sensor_map_for_preset(preset)
            self.state.id = run_id
            self.state.status = SimulationStatus.RUNNING
            self.state.currentPreset = preset_name
            self.state.currentStep = 0
            self.state.currentStepName = None
            self.state.timestamp = utc_now()

            await self._record_event(
                "STATE",
                message=f"Started preset {preset_name}",
                payload={"runId": run_id, "preset": preset_name},
            )

            self.interactive_config = InteractiveConfig()
            self._run_task = asyncio.create_task(self._execute_preset(preset))
            return run_id

    async def _execute_preset(self, preset: PresetDefinition) -> None:
        try:
            for index, step in enumerate(preset.steps, start=1):
                if self._stop_requested:
                    self.state.status = SimulationStatus.STOPPED
                    self.state.timestamp = utc_now()
                    await self._record_event(
                        "STATE",
                        message=f"Preset {preset.name} stopped",
                        payload={"runId": self.state.id, "preset": preset.name},
                    )
                    return

                self.state.currentStep = index
                self.state.currentStepName = step.name
                self.state.timestamp = utc_now()
                await self._record_event(
                    "STATE",
                    message=step.note or f"Executing step {step.name}",
                    payload={
                        "runId": self.state.id,
                        "preset": preset.name,
                        "step": index,
                        "stepName": step.name,
                    },
                )

                if step.awaitRequest is not None:
                    await self._await_step_gate(step)
                else:
                    await self._apply_step_side_effects(step)
                    await asyncio.sleep(step.delayMs / 1000.0)

            self.state.status = SimulationStatus.IDLE
            self.state.timestamp = utc_now()
            await self._record_event(
                "STATE",
                message=f"Preset {preset.name} completed",
                payload={"runId": self.state.id, "preset": preset.name},
            )
        except asyncio.CancelledError:
            self.state.status = SimulationStatus.STOPPED
            self.state.timestamp = utc_now()
            raise
        finally:
            self._stop_requested = False
            self._clear_step_gate()
            self.interactive_config = InteractiveConfig(
                intercepted=set(_DEFAULT_INTERCEPTED)
            )

    def _sensor_map_for_preset(
        self, preset: PresetDefinition | None
    ) -> dict[str, BaseSensor]:
        sensors: dict[str, BaseSensor] = {}

        # Try to obtain an independent instance for each default sensor.
        for sensor_id, plugin in self._default_sensors.items():
            # Prefer plugin-provided `clone()` if available.
            if hasattr(plugin, "clone"):
                try:
                    sensors[sensor_id] = plugin.clone()
                    continue
                except Exception:
                    pass

            # Fallback: re-instantiate the plugin class using a deep copy
            # of its config (if present). If that fails, fall back to the
            # original plugin (best-effort).
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

        # Apply preset overrides. If the plugin exposes `apply_overrides`,
        # use it; otherwise merge overrides into the plugin config.
        for sensor_id, override in preset.sensor_overrides.items():
            if sensor_id not in sensors:
                sensors[sensor_id] = self._make_plugin(sensor_id, {})

            plugin = sensors[sensor_id]
            if hasattr(plugin, "apply_overrides"):
                plugin.apply_overrides(override)
            else:
                # Do not allow changing the sensor `type` via overrides.
                override_filtered = {k: v for k, v in override.items() if k != "type"}
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

    async def _await_step_gate(self, step: PresetStep) -> None:
        assert step.awaitRequest is not None
        event = asyncio.Event()
        self._step_gate = (step.awaitRequest, event, step)
        self.state.waitingForRequest = step.awaitRequest.model_copy()
        timeout = step.delayMs / 1000.0
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            await self._apply_step_side_effects(step)
            await self._record_event(
                "STATE",
                message=f"Step {step.name} gate timed out",
                payload={
                    "runId": self.state.id,
                    "preset": self.state.currentPreset,
                    "step": self.state.currentStep,
                    "stepName": step.name,
                    "gateTimedOut": True,
                },
            )
        finally:
            # Only clear the gate if it still belongs to this step (it may
            # already have been cleared by stop()/reset()).
            current = self._step_gate
            if current is not None and current[1] is event:
                self._step_gate = None
            self.state.waitingForRequest = None

    def _clear_step_gate(self) -> None:
        gate = self._step_gate
        if gate is not None:
            _, event, _ = gate
            event.set()
            self._step_gate = None
        self.state.waitingForRequest = None

    async def _apply_step_side_effects(self, step: PresetStep) -> None:
        self._apply_sensor_updates(step)

        if step.publishDistance is not None:
            distance_plugin = self.sensors.get("distance-conveyor")
            if distance_plugin:
                # Prefer plugin-provided to_sensor_config(); otherwise use a
                # deep copy of the plugin's internal `_cfg` Pydantic model.
                to_sensor_cfg = getattr(distance_plugin, "to_sensor_config", None)
                if callable(to_sensor_cfg):
                    cfg = to_sensor_cfg()
                else:
                    cfg = getattr(distance_plugin, "_cfg", None)
                    if cfg is not None and hasattr(cfg, "model_copy"):
                        cfg = cfg.model_copy(deep=True)

                await self.distance_publisher.publish(cfg, float(step.publishDistance))

    def _apply_sensor_updates(self, step: PresetStep) -> None:
        """Apply sensorUpdates from a `PresetStep` synchronously.

        Sensor updates are synchronous so they are visible immediately to the
        current request context; distance publishes are handled separately.
        """
        for sensor_id, value in step.sensorUpdates.items():
            if sensor_id not in self.sensors:
                self.sensors[sensor_id] = self._make_plugin(sensor_id, {})
            plugin = self.sensors[sensor_id]
            # Prefer the plugin `update()` method when present.
            if hasattr(plugin, "update"):
                plugin.update(value)
            else:
                cfg = getattr(plugin, "_cfg", None)
                if cfg is not None and hasattr(cfg, "model_copy"):
                    try:
                        plugin._cfg = cfg.model_copy(update={"value": value})
                    except Exception:
                        try:
                            setattr(plugin._cfg, "value", value)
                        except Exception:
                            setattr(plugin, "value", value)
                else:
                    setattr(plugin, "value", value)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def get_status(self) -> SimulationState:
        return self.state.model_copy(deep=True)

    async def stop(self) -> None:
        self._stop_requested = True
        self._clear_step_gate()
        await self._record_event(
            "STATE",
            message="Stop requested",
            payload={"runId": self.state.id, "preset": self.state.currentPreset},
        )

    async def reset(self) -> None:
        self._stop_requested = True
        self._clear_step_gate()
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass

        self.state = SimulationState()
        self.sensors = self._sensor_map_for_preset(None)
        await self._record_event(
            "STATE", message="Simulation reset", payload={"status": "reset"}
        )

    # ------------------------------------------------------------------
    # Sensor management
    # ------------------------------------------------------------------
    def get_sensor_configs(self) -> list[SensorConfig]:
        configs: list[SensorConfig] = []
        for key in sorted(self.sensors.keys()):
            plugin = self.sensors[key]
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

    def _make_plugin(self, sensor_id: str, config: dict[str, Any]) -> BaseSensor:
        """Instantiate the sensor plugin for *sensor_id* using *config*.

        Loads the module ``simulated_factory.sensors.<type>`` and instantiates
        the class ``<Type>Sensor``.  Raises :exc:`RuntimeError` with a human-
        readable message if the module or class is missing or construction fails.
        """
        sensor_type = self._infer_sensor_type(sensor_id, config)
        module_name = f"simulated_factory.sensors.{sensor_type.replace('-', '_')}"
        class_name = (
            "".join(w.capitalize() for w in sensor_type.replace("-", "_").split("_"))
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
                f"Sensor plugin module '{module_name}' does not define class '{class_name}'. "
                f"Sensor: '{sensor_id}' (type='{sensor_type}')."
            ) from exc

        # Build a SensorConfig (or plugin-specific config) instance. If the
        # caller already supplied a SensorConfig, use it; otherwise attempt to
        # construct the module-specific config class `<ClassName>Config` and
        # fall back to the generic `SensorConfig` model.
        try:
            if isinstance(config, SensorConfig):
                cfg_obj = config
            else:
                cfg_dict = dict(config or {})
                cfg_dict.setdefault("name", sensor_id)
                cfg_dict.setdefault("type", sensor_type)
                config_cls = getattr(module, class_name + "Config", None)
                if config_cls is None:
                    # Last resort: try a generic SensorConfig
                    cfg_obj = SensorConfig(**cfg_dict)
                else:
                    try:
                        cfg_obj = config_cls(**cfg_dict)
                    except Exception:
                        cfg_obj = SensorConfig(**cfg_dict)

            return cls(sensor_id, cfg_obj)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to instantiate sensor plugin '{class_name}' for sensor '{sensor_id}': {exc}"
            ) from exc

    async def update_sensor(
        self, sensor_id: str, update: SensorUpdateRequest
    ) -> SensorConfig:
        if sensor_id not in self.sensors:
            self.sensors[sensor_id] = self._make_plugin(sensor_id, {})
        plugin = self.sensors[sensor_id]
        update_dict = update.model_dump(exclude_none=True)

        if hasattr(plugin, "apply_update_request"):
            plugin.apply_update_request(update_dict)
        else:
            # Apply common update semantics: set runtime value if provided
            if "value" in update_dict:
                try:
                    plugin.update(update_dict["value"])
                except Exception:
                    pass

            # Merge other fields into the plugin config if possible.
            other = {k: v for k, v in update_dict.items() if k not in ("value", "mode")}
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

        await self._record_event(
            "STATE",
            message=f"Sensor {sensor_id} updated",
            payload={
                "sensorId": sensor_id,
                "config": jsonable_encoder(plugin.to_dict() if hasattr(plugin, "to_dict") else getattr(plugin, "_cfg", None)),
            },
        )

        # Return a SensorConfig instance (prefer plugin.to_sensor_config()).
        if hasattr(plugin, "to_sensor_config"):
            return plugin.to_sensor_config()
        cfg = getattr(plugin, "_cfg", None)
        if cfg is not None and hasattr(cfg, "model_copy"):
            return cfg.model_copy(deep=True)
        return cfg  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------
    async def handle_dobot_commands(
        self, robot_name: str, payload: Any
    ) -> dict[str, Any]:
        command_list = payload if isinstance(payload, list) else [payload]
        correlation_id = f"cmd-{self.state.id}-{self.state.currentStep + 1}"

        intercepted = self.interactive_config.intercepted
        command_types = [
            str(cmd.get("type", "unknown")) if isinstance(cmd, dict) else "unknown"
            for cmd in command_list
        ]
        should_intercept = bool(intercepted) and any(
            ct in intercepted for ct in command_types
        )

        if should_intercept:
            self._pending_counter += 1
            action_id = f"act-{self._pending_counter:04d}"
            action = PendingAction(
                id=action_id,
                robot_name=robot_name,
                commands=list(command_list),
                correlation_id=correlation_id,
            )
            self._pending[action_id] = action

            await self._record_event(
                "PENDING_ACTION",
                message=f"Pending action {action_id} for {robot_name}",
                payload={
                    "actionId": action_id,
                    "robot": robot_name,
                    "commands": command_list,
                    "commandTypes": command_types,
                    "correlationId": correlation_id,
                },
            )

            timeout = max(1, int(self.interactive_config.timeout_seconds))
            try:
                await asyncio.wait_for(action._event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                action.outcome = "failure"
                action.timed_out = True
                self._pending.pop(action_id, None)
                await self._record_event(
                    "ACTION_RESOLVED",
                    message=f"Action {action_id} timed out",
                    payload={
                        "actionId": action_id,
                        "outcome": "failure",
                        "timedOut": True,
                    },
                )

            outcome = action.outcome or "failure"
            if outcome == "success":
                self._apply_commands(robot_name, command_list)
                self.state.timestamp = utc_now()
                await self._record_event(
                    "COMMAND",
                    message=(
                        f"Accepted {len(command_list)} command(s) for {robot_name} "
                        "after interactive resolution"
                    ),
                    payload={"robot": robot_name, "commands": command_list},
                )

            result: dict[str, Any] = {
                "correlationId": correlation_id,
                "outcome": outcome,
            }
            if action.timed_out:
                result["timedOut"] = True
            return result

        self._apply_commands(robot_name, command_list)
        self.state.timestamp = utc_now()
        await self._record_event(
            "COMMAND",
            message=f"Accepted {len(command_list)} command(s) for {robot_name}",
            payload={"robot": robot_name, "commands": command_list},
        )
        return {"correlationId": correlation_id}

    def _apply_commands(self, robot_name: str, command_list: list[Any]) -> None:
        dobot_state = self.state.dobots.setdefault(robot_name, DobotRuntimeState())
        for command in command_list:
            command_type = str(command.get("type", "unknown"))
            match command_type:
                case "move":
                    target = command.get("target", {})
                    dobot_state.position = Position(
                        x=float(target.get("x", dobot_state.position.x)),
                        y=float(target.get("y", dobot_state.position.y)),
                        z=float(target.get("z", dobot_state.position.z)),
                        r=float(target.get("r", dobot_state.position.r)),
                    )
                case "move-relative":
                    offset = command.get("offset", {})
                    dobot_state.position.x += float(offset.get("x", 0.0) or 0.0)
                    dobot_state.position.y += float(offset.get("y", 0.0) or 0.0)
                    dobot_state.position.z += float(offset.get("z", 0.0) or 0.0)
                    dobot_state.position.r += float(offset.get("r", 0.0) or 0.0)
                case "set-speed":
                    dobot_state.speed = float(command.get("speed", dobot_state.speed))
                    if command.get("acceleration") is not None:
                        dobot_state.acceleration = float(command["acceleration"])
                case "suction-cup":
                    dobot_state.suction_enabled = bool(command.get("enabled", False))
                case "run-conveyor":
                    dobot_state.conveyor_speed = float(command.get("speed", 0.0))
                    dobot_state.conveyor_direction = str(
                        command.get("direction", "STOP")
                    )
                case "move-conveyor":
                    dobot_state.conveyor_speed = float(command.get("speed", 0.0))
                    dobot_state.conveyor_distance = float(command.get("distance", 0.0))
                    dobot_state.conveyor_direction = str(
                        command.get("direction", "STOP")
                    )
                case _:
                    self.logger.info(
                        "Ignoring unsupported simulator command type %s", command_type
                    )

            dobot_state.last_command = command_type

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        await self.event_store.append(event_type, **kwargs)

    # ------------------------------------------------------------------
    # Interactive control
    # ------------------------------------------------------------------
    async def resolve_action(
        self, action_id: str, outcome: str, reason: str | None = None
    ) -> PendingAction:
        if outcome not in ("success", "failure"):
            raise ValueError(f"invalid outcome {outcome!r}")
        action = self._pending.get(action_id)
        if action is None:
            raise KeyError(action_id)
        action.outcome = outcome
        action.reason = reason
        action._event.set()
        self._pending.pop(action_id, None)
        await self._record_event(
            "ACTION_RESOLVED",
            message=f"Action {action_id} resolved: {outcome}",
            payload={
                "actionId": action_id,
                "outcome": outcome,
                "reason": reason,
                "timedOut": False,
            },
        )
        return action

    def get_pending_actions(self) -> list[dict[str, Any]]:
        return [action.to_public_dict() for action in self._pending.values()]

    def get_interactive_config(self) -> InteractiveConfig:
        return self.interactive_config.model_copy(deep=True)

    def set_interactive_config(self, config: InteractiveConfig) -> InteractiveConfig:
        self.interactive_config = config
        return self.get_interactive_config()

    def read_color(self, robot_name: str) -> tuple[str, list[int]]:
        plugin = self._sensor_for(robot_name, "color")
        try:
            return plugin.read(self.state.currentStep)  # type: ignore[return-value]
        except TypeError:
            return plugin.read()  # type: ignore[return-value]

    def read_ir(self, robot_name: str) -> bool:
        plugin = self._sensor_for(robot_name, "ir")
        try:
            return plugin.read(self.state.currentStep)  # type: ignore[return-value]
        except TypeError:
            return plugin.read()  # type: ignore[return-value]

    def read_color_sensor_bytes(self) -> dict[str, int]:
        color, raw_color = self.read_color("left")
        rgb = rgb_bytes_from_raw(raw_color or raw_color_from_name(color))
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    async def record_external_event(self, payload: Any) -> None:
        await self._record_event(
            "EVENT", message="External event accepted", payload=payload
        )

    # Path-pattern regex helper moved to `simulated_factory.utils`

    def _matches_gate(self, method: str, path: str) -> bool:
        gate = self._step_gate
        if gate is None:
            return False
        pattern, _event, _step = gate
        if method.upper() != pattern.method.upper():
            return False
        regex = path_pattern_to_regex(pattern.path)
        return regex.match(path) is not None

    # ------------------------------------------------------------------
    # Inventory cache (background poller)
    # ------------------------------------------------------------------
    def get_inventory_cache(self) -> dict:
        """Return the latest cached inventory grid.

        Falls back to a neutral envelope when the cache is cold or the
        inventory service has been unreachable since startup.
        """
        if self._inventory_cache is None:
            return {"grid": None, "rows": 0, "cols": 0}
        return self._inventory_cache

    def start_inventory_poller(self) -> None:
        """Launch the background asyncio.Task that polls inventory every 3 s.

        Idempotent: if a poller task is already running, this is a no-op.
        """
        if (
            self._inventory_poll_task is not None
            and not self._inventory_poll_task.done()
        ):
            return
        self._inventory_poll_task = asyncio.create_task(self._inventory_poll_loop())

    async def stop_inventory_poller(self) -> None:
        task = self._inventory_poll_task
        self._inventory_poll_task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # pragma: no cover - defensive
            pass

    async def _inventory_poll_loop(self) -> None:
        url = self._inventory_url.rstrip("/") + "/inventory"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                while True:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            self._inventory_cache = response.json()
                    except Exception:
                        # Swallow all transient errors; keep last cache value.
                        pass
                    await asyncio.sleep(3.0)
        except asyncio.CancelledError:
            raise

    def _sensor_for(self, robot_name: str, prefix: str) -> BaseSensor:
        sensor_id = f"{prefix}-{robot_name}"
        if sensor_id not in self.sensors:
            self.sensors[sensor_id] = self._make_plugin(sensor_id, {})
        return self.sensors[sensor_id]

    def _infer_sensor_type(self, sensor_id: str, config: dict[str, Any]) -> str:
        """Infer the plugin type from config or sensor-id prefix."""
        if config.get("type"):
            return str(config["type"])
        for prefix, sensor_type in _TYPE_INFERENCE_RULES:
            if sensor_id.startswith(prefix):
                return sensor_type
        return "generic"
