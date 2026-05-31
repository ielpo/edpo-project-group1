from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

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
    utc_now,
)
from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.actuators.base import BaseActuator
from simulated_factory.sensor_registry import SensorRegistry
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
        inventory_poller: Any = None,
    ):
        self.event_store = event_store
        self._mqtt_publisher = mqtt_publisher
        self._event_bridge = event_bridge
        self._inventory_poller = inventory_poller

        self._sensor_registry = SensorRegistry(config_path, mqtt_publisher=mqtt_publisher)
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
        self._pending_action: PendingAction | None = None
        self._interactive_config = InteractiveConfig()

        self._actuator_registry = ActuatorRegistry()
        self._actuators: dict[str, BaseActuator] = self._actuator_registry.actuators()

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
                name: cast(DobotRuntimeState, actuator.state())
                for name, actuator in self._actuators.items()
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
            self._sensor_registry.reset()

            await self._record_event(
                "STATE",
                message=f"Started preset {preset_name}",
                payload={"runId": self._run_id, "preset": preset_name},
            )

            await self._sensor_registry.activate()
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

        await self._sensor_registry.deactivate()
        self._status = SimulationStatus.IDLE
        self._run_id = "run-0000"
        self._current_preset = None
        self._current_step = 0
        self._current_step_name = None
        self._stop_requested = False
        self._run_task = None

        self._step_gate = None
        self._waiting_for_request = None
        self._pending_action = None
        self._interactive_config = InteractiveConfig()

        self._sensor_registry.reset()
        self._actuators = self._actuator_registry.actuators()

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
            await self._sensor_registry.deactivate()
            self._interactive_config = InteractiveConfig(
                intercepted=set(_DEFAULT_INTERCEPTED)
            )

    async def _run_step(self, step: PresetStep, speed: float) -> None:
        if step.awaitRequest is not None:
            await self._await_gate(step, speed)
            return

        self._sensor_registry.apply_updates(step.sensorUpdates)

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
            self._sensor_registry.apply_updates(step.sensorUpdates)
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

        self._sensor_registry.apply_updates(step.sensorUpdates)
        event.set()
        return True



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
            pending_action = self._pending_action
            if pending_action is not None:
                reason = (
                    f"pending action {pending_action.id} must be resolved first"
                )
                await self._record_event(
                    "ACTION_RESOLVED",
                    message=(
                        "Rejected interactive command while another action "
                        "is pending"
                    ),
                    payload={
                        "actionId": pending_action.id,
                        "outcome": "failure",
                        "reason": reason,
                        "timedOut": False,
                        "correlationId": correlation_id,
                        "robot": robot_name,
                        "commands": command_list,
                        "commandTypes": command_types,
                    },
                )
                return {
                    "correlationId": correlation_id,
                    "outcome": "failure",
                    "reason": reason,
                }

            action_id = "0"
            action = PendingAction(
                id=action_id,
                robot_name=robot_name,
                commands=list(command_list),
                correlation_id=correlation_id,
            )
            self._pending_action = action

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
            self._sensor_registry.pause()
            try:
                resolved = await action.wait_for_resolution(timeout=timeout)
            finally:
                self._sensor_registry.resume()
            if not resolved:
                action.outcome = "failure"
                action.timed_out = True
                if self._pending_action is action:
                    self._pending_action = None
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
                self._actuators[robot_name].apply(command_list)
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

        self._actuators[robot_name].apply(command_list)
        await self._record_event(
            "COMMAND",
            message=f"Accepted {len(command_list)} command(s) for {robot_name}",
            payload={"robot": robot_name, "commands": command_list},
        )
        return {"correlationId": correlation_id}

    async def resolve_action(
        self, action_id: str, outcome: str, reason: str | None = None
    ) -> PendingAction:
        if outcome not in ("success", "failure"):
            raise ValueError(f"invalid outcome {outcome!r}")

        action = self._pending_action
        if action is None or action.id != action_id:
            raise KeyError(action_id)

        action.resolve(outcome, reason)
        if self._pending_action is action:
            self._pending_action = None

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
        action = self._pending_action
        if action is None:
            return []
        return [action.to_public_dict()]

    def get_interactive_config(self) -> InteractiveConfig:
        return self._interactive_config.model_copy(deep=True)

    def set_interactive_config(self, config: InteractiveConfig) -> InteractiveConfig:
        self._interactive_config = config
        return self.get_interactive_config()

    def get_sensor_configs(self) -> list[SensorConfig]:
        return self._sensor_registry.configs()

    async def update_sensor(
        self, sensor_id: str, update: SensorUpdateRequest
    ) -> SensorConfig:
        plugin = self._sensor_registry.get_or_create(sensor_id)
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

    def read_color(self, robot_name: str) -> tuple[str, list[int]]:
        plugin = self._sensor_registry.get_or_create(f"color-{robot_name}")
        return cast(tuple[str, list[int]], plugin.read(step=self._current_step))

    def read_ir(self, robot_name: str) -> bool:
        plugin = self._sensor_registry.get_or_create(f"ir-{robot_name}")
        return bool(plugin.read(step=self._current_step))

    def read_color_sensor_bytes(self) -> dict[str, int]:
        color, raw_color = self.read_color("left")
        rgb = rgb_bytes_from_raw(raw_color or raw_color_from_name(color))
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    def get_dobot_state(self, robot_name: str) -> DobotRuntimeState:
        return cast(DobotRuntimeState, self._actuators[robot_name].state())

    def get_inventory_cache(self) -> dict[str, Any]:
        if self._inventory_poller is None:
            return {"grid": None, "rows": 0, "cols": 0}
        return self._inventory_poller.get_cache()

    async def record_external_event(self, payload: Any) -> None:
        await self._record_event(
            "EVENT", message="External event accepted", payload=payload
        )

    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        await self.event_store.append(event_type, **kwargs)
