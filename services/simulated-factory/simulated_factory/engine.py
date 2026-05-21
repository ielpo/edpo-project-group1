from __future__ import annotations

import asyncio
import copy
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi.encoders import jsonable_encoder

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.events import EventBridge, EventStore
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


_DEFAULT_INTERCEPTED: frozenset[str] = frozenset(
    {"move", "move-relative", "set-speed", "suction-cup", "run-conveyor", "move-conveyor"}
)


class SimulationEngine:
    def __init__(
        self,
        *,
        config_path: str,
        event_store: EventStore,
        distance_publisher: DistancePublisher,
        event_bridge: EventBridge,
        inventory_url: str | None = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self.event_store = event_store
        self.distance_publisher = distance_publisher
        self.event_bridge = event_bridge
        self._inventory_url = (
            inventory_url
            if inventory_url is not None
            else os.getenv("INVENTORY_URL", "http://localhost:8103")
        )
        self.state = self._new_state()
        self._default_sensors: dict[str, SensorConfig] = {}
        self.sensors: dict[str, SensorConfig] = {}
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
        self.reload_config()

    def reload_config(self) -> None:
        payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        defaults = payload.get("defaults", {}).get("sensors", {})
        presets = payload.get("presets", {})

        self._default_sensors = {
            sensor_id: SensorConfig(sensorId=sensor_id, **config)
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

    def list_presets(self) -> list[dict[str, object]]:
        return [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in self.presets.values()
        ]

    def get_status(self) -> SimulationState:
        return self.state.model_copy(deep=True)

    def get_sensor_configs(self) -> list[SensorConfig]:
        return [
            self.sensors[key].model_copy(deep=True)
            for key in sorted(self.sensors.keys())
        ]

    def get_dobot_state(self, robot_name: str) -> DobotRuntimeState:
        return self.state.dobots.setdefault(robot_name, DobotRuntimeState()).model_copy(
            deep=True
        )

    async def update_sensor(
        self, sensor_id: str, update: SensorUpdateRequest
    ) -> SensorConfig:
        sensor = self.sensors.setdefault(sensor_id, SensorConfig(sensorId=sensor_id))
        payload = update.model_dump(exclude_none=True)
        for field_name, value in payload.items():
            setattr(sensor, field_name, value)

        await self._record_event(
            "STATE",
            message=f"Sensor {sensor_id} updated",
            payload={"sensorId": sensor_id, "config": jsonable_encoder(sensor)},
        )
        return sensor.model_copy(deep=True)

    async def run_preset(self, preset_name: str, speed: str = "normal") -> str:
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
                payload={"runId": run_id, "preset": preset_name, "speed": speed},
            )

            self.interactive_config = InteractiveConfig()
            self._run_task = asyncio.create_task(self._execute_preset(preset, speed))
            return run_id

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

        self.state = self._new_state()
        self.sensors = self._sensor_map_for_preset(None)
        await self._record_event(
            "STATE", message="Simulation reset", payload={"status": "reset"}
        )

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
        sensor = self._sensor_for(robot_name, "color")
        color = str(self._sensor_value(sensor, default="YELLOW") or "YELLOW").upper()
        raw_color = sensor.raw_color or self._raw_color_from_name(color)
        return color, raw_color

    def read_ir(self, robot_name: str) -> bool:
        sensor = self._sensor_for(robot_name, "ir")
        return bool(self._sensor_value(sensor, default=True))

    def read_color_sensor_bytes(self) -> dict[str, int]:
        color, raw_color = self.read_color("left")
        rgb = self._rgb_bytes_from_raw(raw_color or self._raw_color_from_name(color))
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    async def record_external_event(self, payload: Any) -> None:
        await self._record_event(
            "EVENT", message="External event accepted", payload=payload
        )

    async def _execute_preset(self, preset: PresetDefinition, speed: str) -> None:
        try:
            multiplier = self._speed_multiplier(speed)
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
                    await self._await_step_gate(step, multiplier)
                else:
                    await self._apply_step_side_effects(step)
                    await asyncio.sleep((step.delayMs / 1000.0) * multiplier)

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

    async def _apply_step_side_effects(self, step: PresetStep) -> None:
        for sensor_id, value in step.sensorUpdates.items():
            sensor = self.sensors.setdefault(
                sensor_id, SensorConfig(sensorId=sensor_id)
            )
            sensor.value = value

        if step.publishDistance is not None:
            distance_sensor = self.sensors.get("distance-conveyor")
            if distance_sensor:
                await self.distance_publisher.publish(
                    distance_sensor, float(step.publishDistance)
                )

    async def _await_step_gate(self, step: PresetStep, multiplier: float) -> None:
        assert step.awaitRequest is not None
        event = asyncio.Event()
        self._step_gate = (step.awaitRequest, event, step)
        self.state.waitingForRequest = step.awaitRequest.model_copy()
        timeout = (step.delayMs / 1000.0) * multiplier
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

    @staticmethod
    def _path_pattern_to_regex(pattern: str) -> re.Pattern[str]:
        # Convert `{name}` placeholders into a non-slash segment match.
        escaped = re.escape(pattern)
        # `re.escape` turns `{name}` into `\{name\}`
        regex = re.sub(r"\\\{[^/\\}]+\\\}", r"[^/]+", escaped)
        return re.compile(f"^{regex}$")

    def _matches_gate(self, method: str, path: str) -> bool:
        gate = self._step_gate
        if gate is None:
            return False
        pattern, _event, _step = gate
        if method.upper() != pattern.method.upper():
            return False
        regex = self._path_pattern_to_regex(pattern.path)
        return regex.match(path) is not None

    def fire_gate_if_matches(self, method: str, path: str) -> bool:
        gate = self._step_gate
        if gate is None or not self._matches_gate(method, path):
            return False
        _pattern, event, step = gate
        # Apply side-effects synchronously (sensor updates) and schedule the
        # async distance publish so middleware doesn't block.
        for sensor_id, value in step.sensorUpdates.items():
            sensor = self.sensors.setdefault(
                sensor_id, SensorConfig(sensorId=sensor_id)
            )
            sensor.value = value
        if step.publishDistance is not None:
            distance_sensor = self.sensors.get("distance-conveyor")
            if distance_sensor is not None:
                asyncio.create_task(
                    self.distance_publisher.publish(
                        distance_sensor, float(step.publishDistance)
                    )
                )
        event.set()
        # Don't clear _step_gate here; _await_step_gate's finally clause does it.
        return True

    def _new_state(self) -> SimulationState:
        return SimulationState()

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
        if self._inventory_poll_task is not None and not self._inventory_poll_task.done():
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

    def _sensor_map_for_preset(
        self, preset: PresetDefinition | None
    ) -> dict[str, SensorConfig]:
        sensors = {
            sensor_id: config.model_copy(deep=True)
            for sensor_id, config in self._default_sensors.items()
        }
        if preset is None:
            return sensors

        for sensor_id, override in preset.sensor_overrides.items():
            sensor = sensors.setdefault(sensor_id, SensorConfig(sensorId=sensor_id))
            updated = copy.deepcopy(override)
            for field_name, value in updated.items():
                setattr(sensor, field_name, value)
        return sensors

    def _sensor_for(self, robot_name: str, prefix: str) -> SensorConfig:
        sensor_id = f"{prefix}-{robot_name}"
        return self.sensors.get(sensor_id) or self.sensors.setdefault(
            sensor_id, SensorConfig(sensorId=sensor_id)
        )

    def _sensor_value(self, sensor: SensorConfig, default: Any) -> Any:
        if sensor.mode == "scripted" and sensor.scripted_values:
            index = max(self.state.currentStep - 1, 0)
            index = min(index, len(sensor.scripted_values) - 1)
            return sensor.scripted_values[index]

        return sensor.value if sensor.value is not None else default

    def _raw_color_from_name(self, color: str) -> list[int]:
        palette = {
            "RED": [1, 0, 0],
            "GREEN": [0, 1, 0],
            "BLUE": [0, 0, 1],
            "YELLOW": [1, 1, 0],
        }
        return palette.get(color.upper(), [0, 0, 0])

    def _rgb_bytes_from_raw(self, raw_color: list[int]) -> tuple[int, int, int]:
        padded = (raw_color + [0, 0, 0])[:3]
        return tuple(255 if value else 0 for value in padded)  # type: ignore[return-value]

    def _speed_multiplier(self, speed: str) -> float:
        return {
            "slow": 2.0,
            "normal": 1.0,
            "fast": 0.5,
        }.get(speed, 1.0)

    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        entry = await self.event_store.append(event_type, **kwargs)
        await self.event_bridge.emit(jsonable_encoder(entry))
