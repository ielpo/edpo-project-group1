from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, cast

import httpx
from fastapi.encoders import jsonable_encoder

from simulated_factory.events import EventStore
from simulated_factory.models import (
    AwaitRequest,
    DobotRuntimeState,
    InteractiveConfig,
    PendingAction,
    PresetDefinition,
    PresetStep,
    SensorConfig,
    SensorUpdateRequest,
    SimulationState,
    SimulationStatus,
    Position,
    utc_now,
)
from simulated_factory.sensor_registry import SensorRegistry
from simulated_factory.sensors.base import BaseSensor, MqttSensor
from simulated_factory.utils import (
    path_pattern_to_regex,
    raw_color_from_name,
    rgb_bytes_from_raw,
)

logger = logging.getLogger(__name__)

# Default to intercepting all known command types between runs so the UI
# always regains control unless explicitly configured otherwise.
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
        mqtt_publisher: Any,
        event_bridge: Any = None,
        inventory_url: str | None = None,
    ):
        self.event_store = event_store
        self._mqtt_publisher = mqtt_publisher
        self._event_bridge = event_bridge

        self._sensor_registry = SensorRegistry(config_path)
        self._presets: dict[str, PresetDefinition] = self._sensor_registry.get_presets()

        self._status: SimulationStatus = SimulationStatus.IDLE
        self._run_id: str = "run-0000"
        self._run_counter: int = 0
        self._current_preset: str | None = None
        self._current_step: int = 0
        self._current_step_name: str | None = None
        self._stop_requested: bool = False
        self._run_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

        self._step_gate: tuple[AwaitRequest, asyncio.Event, PresetStep] | None = None
        self._waiting_for_request: AwaitRequest | None = None
        self._pending: dict[str, PendingAction] = {}
        self._pending_counter: int = 0
        self._interactive_config = InteractiveConfig()

        self._sensors: dict[str, BaseSensor] = self._sensor_registry.for_preset(None)
        self._wire_sensors(self._sensors)
        self._dobots: dict[str, DobotRuntimeState] = {
            "left": DobotRuntimeState(),
            "right": DobotRuntimeState(),
        }
        self._inventory_cache: dict[str, Any] | None = None
        self._inventory_task: asyncio.Task[None] | None = None
        self._inventory_url = inventory_url or os.getenv(
            "INVENTORY_URL", "http://localhost:8103"
        )

    @property
    def presets(self) -> dict[str, PresetDefinition]:
        return self._presets

    @property
    def interactive_config(self) -> InteractiveConfig:
        return self._interactive_config

    @interactive_config.setter
    def interactive_config(self, value: InteractiveConfig) -> None:
        self._interactive_config = value

    def get_status(self) -> SimulationState:
        return SimulationState(
            id=self._run_id,
            status=self._status,
            currentPreset=self._current_preset,
            currentStep=self._current_step,
            currentStepName=self._current_step_name,
            timestamp=utc_now(),
            dobots={
                name: dobot.model_copy(deep=True)
                for name, dobot in self._dobots.items()
            },
            waitingForRequest=(
                self._waiting_for_request.model_copy(deep=True)
                if self._waiting_for_request is not None
                else None
            ),
        )

    def list_presets(self) -> list[dict[str, object]]:
        return [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in self._presets.values()
        ]

    async def run_preset(self, preset_name: str, speed: float = 1.0) -> str:
        preset = self._presets.get(preset_name)
        if preset is None:
            raise KeyError(preset_name)

        async with self._lock:
            if self._run_task is not None and not self._run_task.done():
                raise RuntimeError("simulation already running")

            self._run_counter += 1
            self._run_id = f"run-{self._run_counter:04d}"
            self._status = SimulationStatus.RUNNING
            self._current_preset = preset_name
            self._current_step = 0
            self._current_step_name = None
            self._stop_requested = False
            self._interactive_config = InteractiveConfig()
            self._sensors = self._sensor_registry.for_preset(preset)
            self._wire_sensors(self._sensors)

            await self._record_event(
                "STATE",
                message=f"Started preset {preset_name}",
                payload={"runId": self._run_id, "preset": preset_name},
            )

            await self._start_sensor_tasks()
            self._run_task = asyncio.create_task(self._execute_preset(preset, speed))
            return self._run_id

    async def stop(self) -> None:
        self._stop_requested = True
        self._clear_step_gate()
        await self._record_event(
            "STATE",
            message="Stop requested",
            payload={"runId": self._run_id, "preset": self._current_preset},
        )

    async def reset(self) -> None:
        self._stop_requested = True
        self._clear_step_gate()

        if self._run_task is not None and not self._run_task.done():
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass

        await self._stop_sensor_tasks()
        self._status = SimulationStatus.IDLE
        self._run_id = "run-0000"
        self._current_preset = None
        self._current_step = 0
        self._current_step_name = None
        self._stop_requested = False
        self._run_task = None

        self._step_gate = None
        self._waiting_for_request = None
        self._pending.clear()
        self._pending_counter = 0
        self._interactive_config = InteractiveConfig()

        self._sensors = self._sensor_registry.for_preset(None)
        self._wire_sensors(self._sensors)
        self._dobots = {
            "left": DobotRuntimeState(),
            "right": DobotRuntimeState(),
        }

        await self._record_event(
            "STATE", message="Simulation reset", payload={"status": "reset"}
        )

    async def _execute_preset(
        self, preset: PresetDefinition, speed: float = 1.0
    ) -> None:
        try:
            for index, step in enumerate(preset.steps, start=1):
                if self._stop_requested:
                    self._status = SimulationStatus.STOPPED
                    await self._record_event(
                        "STATE",
                        message=f"Preset {preset.name} stopped",
                        payload={
                            "runId": self._run_id,
                            "preset": preset.name,
                        },
                    )
                    return

                self._current_step = index
                self._current_step_name = step.name

                await self._record_event(
                    "STATE",
                    message=step.note or f"Executing step {step.name}",
                    payload={
                        "runId": self._run_id,
                        "preset": preset.name,
                        "step": index,
                        "stepName": step.name,
                    },
                )

                await self._run_step(step, speed)

            self._status = SimulationStatus.IDLE
            await self._record_event(
                "STATE",
                message=f"Preset {preset.name} completed",
                payload={
                    "runId": self._run_id,
                    "preset": preset.name,
                },
            )
        except asyncio.CancelledError:
            self._status = SimulationStatus.STOPPED
            raise
        finally:
            self._stop_requested = False
            self._clear_step_gate()
            await self._stop_sensor_tasks()
            self._interactive_config = InteractiveConfig(
                intercepted=set(_DEFAULT_INTERCEPTED)
            )

    async def _run_step(self, step: PresetStep, speed: float) -> None:
        if step.awaitRequest is not None:
            await self._await_gate(step, speed)
            return

        self._apply_sensor_updates(step)

        delay = step.delayMs / 1000.0
        if speed > 0:
            delay /= speed
        await asyncio.sleep(delay)

    async def _await_gate(self, step: PresetStep, speed: float) -> None:
        assert step.awaitRequest is not None

        event = asyncio.Event()
        self._step_gate = (step.awaitRequest, event, step)
        self._waiting_for_request = step.awaitRequest.model_copy(deep=True)

        timeout = step.delayMs / 1000.0
        if speed > 0:
            timeout /= speed

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self._apply_sensor_updates(step)
            await self._record_event(
                "STATE",
                message=f"Step {step.name} gate timed out",
                payload={
                    "runId": self._run_id,
                    "preset": self._current_preset,
                    "step": self._current_step,
                    "stepName": step.name,
                    "gateTimedOut": True,
                },
            )
        finally:
            gate = self._step_gate
            if gate is not None and gate[1] is event:
                self._step_gate = None
            self._waiting_for_request = None

    def _clear_step_gate(self) -> None:
        gate = self._step_gate
        if gate is not None:
            _, event, _ = gate
            event.set()
            self._step_gate = None
        self._waiting_for_request = None

    def _matches_gate(self, method: str, path: str) -> bool:
        gate = self._step_gate
        if gate is None:
            return False

        pattern, _event, _step = gate
        if method.upper() != pattern.method.upper():
            return False

        regex = path_pattern_to_regex(pattern.path)
        return regex.match(path) is not None

    def fire_gate_if_matches(self, method: str, path: str) -> bool:
        gate = self._step_gate
        if gate is None:
            return False

        pattern, event, step = gate
        if method.upper() != pattern.method.upper():
            return False

        regex = path_pattern_to_regex(pattern.path)
        if regex.match(path) is None:
            return False

        self._apply_sensor_updates(step)
        event.set()
        return True

    def _apply_sensor_updates(self, step: PresetStep) -> None:
        for sensor_id, value in step.sensorUpdates.items():
            if sensor_id not in self._sensors:
                sensor = self._sensor_registry.make(sensor_id, {})
                if isinstance(sensor, MqttSensor):
                    sensor.wire(self._mqtt_publisher)
                self._sensors[sensor_id] = sensor
            self._sensors[sensor_id].update(value)

    def _wire_sensors(self, sensors: dict[str, BaseSensor]) -> None:
        for sensor in sensors.values():
            if isinstance(sensor, MqttSensor):
                sensor.wire(self._mqtt_publisher)

    async def _start_sensor_tasks(self) -> None:
        for sensor in self._sensors.values():
            if isinstance(sensor, MqttSensor):
                await sensor.start_task()

    async def _stop_sensor_tasks(self) -> None:
        for sensor in self._sensors.values():
            if isinstance(sensor, MqttSensor):
                await sensor.stop_task()

    def _pause_sensor_tasks(self) -> None:
        for sensor in self._sensors.values():
            if isinstance(sensor, MqttSensor):
                sensor.pause_task()

    def _resume_sensor_tasks(self) -> None:
        for sensor in self._sensors.values():
            if isinstance(sensor, MqttSensor):
                sensor.resume_task()

    async def handle_dobot_commands(
        self, robot_name: str, payload: Any
    ) -> dict[str, Any]:
        command_list = payload if isinstance(payload, list) else [payload]
        correlation_id = f"cmd-{self._run_id}-{self._current_step + 1}"

        intercepted = self._interactive_config.intercepted
        command_types = [
            str(cmd.get("type", "unknown")) if isinstance(cmd, dict) else "unknown"
            for cmd in command_list
        ]
        should_intercept = bool(intercepted) and any(
            cmd_type in intercepted for cmd_type in command_types
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

            timeout = max(1, int(self._interactive_config.timeout_seconds))
            self._pause_sensor_tasks()
            try:
                resolved = await action.wait_for_resolution(timeout=timeout)
            finally:
                self._resume_sensor_tasks()
            if not resolved:
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
                self._apply_dobot_commands(robot_name, command_list)
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

        self._apply_dobot_commands(robot_name, command_list)
        await self._record_event(
            "COMMAND",
            message=f"Accepted {len(command_list)} command(s) for {robot_name}",
            payload={"robot": robot_name, "commands": command_list},
        )
        return {"correlationId": correlation_id}

    def _apply_dobot_commands(self, robot_name: str, command_list: list[Any]) -> None:
        dobot_state = self._dobots.setdefault(robot_name, DobotRuntimeState())
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
                    logger.info(
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

        action.resolve(outcome, reason)
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
        return self._interactive_config.model_copy(deep=True)

    def set_interactive_config(self, config: InteractiveConfig) -> InteractiveConfig:
        self._interactive_config = config
        return self.get_interactive_config()

    def get_sensor_configs(self) -> list[SensorConfig]:
        return [
            self._sensors[sensor_id].to_config()
            for sensor_id in sorted(self._sensors.keys())
        ]

    async def update_sensor(
        self, sensor_id: str, update: SensorUpdateRequest
    ) -> SensorConfig:
        if sensor_id not in self._sensors:
            sensor = self._sensor_registry.make(sensor_id, {})
            if isinstance(sensor, MqttSensor):
                sensor.wire(self._mqtt_publisher)
            self._sensors[sensor_id] = sensor

        plugin = self._sensors[sensor_id]
        plugin.apply_update(update.model_dump(exclude_none=True))

        await self._record_event(
            "STATE",
            message=f"Sensor {sensor_id} updated",
            payload={
                "sensorId": sensor_id,
                "config": jsonable_encoder(plugin.to_dict()),
            },
        )

        return plugin.to_config()

    def _sensor_for(self, robot_name: str, prefix: str) -> BaseSensor:
        sensor_id = f"{prefix}-{robot_name}"
        if sensor_id not in self._sensors:
            sensor = self._sensor_registry.make(sensor_id, {})
            if isinstance(sensor, MqttSensor):
                sensor.wire(self._mqtt_publisher)
            self._sensors[sensor_id] = sensor
        return self._sensors[sensor_id]

    def read_color(self, robot_name: str) -> tuple[str, list[int]]:
        plugin = self._sensor_for(robot_name, "color")
        return cast(tuple[str, list[int]], plugin.read(step=self._current_step))

    def read_ir(self, robot_name: str) -> bool:
        plugin = self._sensor_for(robot_name, "ir")
        return bool(plugin.read(step=self._current_step))

    def read_color_sensor_bytes(self) -> dict[str, int]:
        color, raw_color = self.read_color("left")
        rgb = rgb_bytes_from_raw(raw_color or raw_color_from_name(color))
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    def get_dobot_state(self, robot_name: str) -> DobotRuntimeState:
        return self._dobots.setdefault(robot_name, DobotRuntimeState()).model_copy(
            deep=True
        )

    def get_inventory_cache(self) -> dict[str, Any]:
        if self._inventory_cache is None:
            return {"grid": None, "rows": 0, "cols": 0}
        return self._inventory_cache

    def start_inventory_poller(self) -> None:
        if self._inventory_task is not None and not self._inventory_task.done():
            return
        self._inventory_task = asyncio.create_task(self._inventory_poll_loop())

    async def stop_inventory_poller(self) -> None:
        task = self._inventory_task
        self._inventory_task = None
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
                            self._inventory_cache = response.json()
                    except Exception:
                        pass
                    await asyncio.sleep(3.0)
        except asyncio.CancelledError:
            raise

    async def record_external_event(self, payload: Any) -> None:
        await self._record_event(
            "EVENT", message="External event accepted", payload=payload
        )

    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        await self.event_store.append(event_type, **kwargs)
