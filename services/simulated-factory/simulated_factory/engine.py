from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from fastapi.encoders import jsonable_encoder

from simulated_factory.events import EventStore
from simulated_factory.models import (
    AwaitTrigger,
    EngineLifecycleState,
    PendingAction,
    PresetDefinition,
    PresetStep,
    SensorConfig,
    SensorUpdateRequest,
    SimulationStatus,
    TriggerEvent,
    utc_now,
)
from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.sensor_registry import SensorRegistry
from simulated_factory.utils import (
    path_pattern_to_regex,
)

logger = logging.getLogger(__name__)


class SimulationEngine:
    def __init__(
        self,
        *,
        event_store: EventStore,
        mqtt_publisher: Any,
        sensor_registry: "SensorRegistry",
        actuator_registry: "ActuatorRegistry",
    ):
        self.event_store = event_store
        self._mqtt_publisher = mqtt_publisher

        self._sensor_registry = sensor_registry
        self._actuator_registry = actuator_registry
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

        # Unified gate state.
        self._active_gate: (
            tuple[AwaitTrigger, asyncio.Event, PresetStep] | None
        ) = None
        self._gate_aborted: bool = False
        self._pending_action: PendingAction | None = None
        self._action_counter: int = 0

    @property
    def presets(self) -> dict[str, PresetDefinition]:
        return self._presets

    def get_status(self) -> EngineLifecycleState:
        gate = self._active_gate
        return EngineLifecycleState(
            id=self._run_id,
            status=self._status,
            currentPreset=self._current_preset,
            currentStep=self._current_step,
            currentStepName=self._current_step_name,
            timestamp=utc_now(),
            activeGate=gate[0].model_copy(deep=True) if gate is not None else None,
        )

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
        self._abort_active_gate()
        await self._record_event(
            "STATE",
            message="Stop requested",
            payload={"runId": self._run_id, "preset": self._current_preset},
        )

    async def reset(self) -> None:
        self._stop_requested = True
        self._abort_active_gate()

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

        self._active_gate = None
        self._gate_aborted = False
        self._pending_action = None

        self._sensor_registry.reset()
        self._actuator_registry.reset()

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

            if self._stop_requested:
                self._status = SimulationStatus.STOPPED
            else:
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
            self._active_gate = None
            self._gate_aborted = False
            self._pending_action = None
            await self._sensor_registry.deactivate()

    async def _run_step(self, step: PresetStep, speed: float) -> None:
        # Sensor updates apply immediately, regardless of gating.
        if step.sensorUpdates:
            self._sensor_registry.apply_updates(step.sensorUpdates)

        if step.awaitTrigger is not None:
            await self._await_gate(step, speed)
            return

        delay_ms = step.delayMs if step.delayMs is not None else 0
        delay = delay_ms / 1000.0
        if speed > 0:
            delay /= speed
        if delay > 0:
            await asyncio.sleep(delay)

    async def _await_gate(self, step: PresetStep, speed: float) -> None:
        trigger = step.awaitTrigger
        assert trigger is not None

        event = asyncio.Event()
        self._active_gate = (trigger, event, step)
        self._gate_aborted = False

        # Surface the gate via PendingAction for the UI snapshot.
        self._action_counter += 1
        action = PendingAction(
            id=f"gate-{self._action_counter}",
            step_name=step.name,
            trigger_type=trigger.type,
            trigger_spec=_trigger_spec(trigger),
            timeout_ms=trigger.timeoutMs,
        )
        self._pending_action = action

        await self._record_event(
            "PENDING_ACTION",
            message=f"Gate waiting at step {step.name} ({trigger.type})",
            payload={
                "actionId": action.id,
                "stepName": step.name,
                "triggerType": trigger.type,
                "triggerSpec": action.trigger_spec,
                "timeoutMs": trigger.timeoutMs,
            },
        )

        timeout = trigger.timeoutMs / 1000.0
        if speed > 0:
            timeout /= speed

        timed_out = False
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
        finally:
            gate = self._active_gate
            if gate is not None and gate[1] is event:
                self._active_gate = None
            self._pending_action = None

        if self._stop_requested:
            # Stop/reset took precedence; let the outer loop handle teardown.
            return

        if timed_out or self._gate_aborted:
            reason = "rejected" if self._gate_aborted else "timed out"
            await self._record_event(
                "ACTION_RESOLVED",
                message=f"Gate {reason} at step {step.name}",
                payload={
                    "actionId": action.id,
                    "stepName": step.name,
                    "triggerType": trigger.type,
                    "outcome": "failure",
                    "timedOut": timed_out,
                    "rejected": self._gate_aborted,
                    "gateAborted": True,
                },
            )
            self._gate_aborted = False
            # Abort preset run.
            self._stop_requested = True
            return

        await self._record_event(
            "ACTION_RESOLVED",
            message=f"Gate fired at step {step.name}",
            payload={
                "actionId": action.id,
                "stepName": step.name,
                "triggerType": trigger.type,
                "outcome": "success",
            },
        )

    def _abort_active_gate(self) -> None:
        """Wake any waiter without firing the gate.

        Used by stop/reset to cancel a pending wait. The waiter's ``finally``
        block will tear down ``_active_gate``.
        """
        gate = self._active_gate
        if gate is not None:
            _, event, _ = gate
            event.set()

    # ------------------------------------------------------------------
    # Gate firing
    # ------------------------------------------------------------------

    def try_fire_gate(self, event: TriggerEvent) -> bool:
        """Fire the active gate if the given trigger event matches.

        Returns True if a gate was fired, False otherwise. Safe to call when
        no gate is active.
        """
        gate = self._active_gate
        if gate is None:
            return False

        trigger, async_event, _step = gate
        if event.type != trigger.type:
            return False

        if trigger.type == "http":
            if event.method is None or event.path is None:
                return False
            if event.method.upper() != (trigger.method or "").upper():
                return False
            regex = path_pattern_to_regex(trigger.path or "")
            if regex.match(event.path) is None:
                return False
        elif trigger.type == "kafka":
            if event.topic is None or event.topic != trigger.topic:
                return False
        # manual: matches unconditionally on type.

        async_event.set()
        return True

    def reject_active_gate(self) -> bool:
        """Reject the active manual gate \u2014 aborts the preset.

        Returns True if a manual gate was rejected, False otherwise.
        """
        gate = self._active_gate
        if gate is None:
            return False
        trigger, async_event, _step = gate
        if trigger.type != "manual":
            return False
        self._gate_aborted = True
        async_event.set()
        return True

    def get_active_gate(self) -> AwaitTrigger | None:
        gate = self._active_gate
        return gate[0].model_copy(deep=True) if gate is not None else None

    # ------------------------------------------------------------------
    # Actuator commands (no interception)
    # ------------------------------------------------------------------

    async def handle_actuator_commands(
        self, robot_name: str, payload: Any
    ) -> dict[str, Any]:
        command_list = payload if isinstance(payload, list) else [payload]
        correlation_id = f"cmd-{self._run_id}-{self._current_step + 1}"

        self._actuator_registry.apply_commands(robot_name, command_list)
        await self._record_event(
            "COMMAND",
            message=f"Accepted {len(command_list)} command(s) for {robot_name}",
            payload={"robot": robot_name, "commands": command_list},
        )
        return {"correlationId": correlation_id}

    def get_pending_actions(self) -> list[dict[str, Any]]:
        action = self._pending_action
        if action is None:
            return []
        return [action.to_public_dict()]

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
        return cast(tuple[str, list[int]], plugin.read())

    def read_ir(self, robot_name: str) -> bool:
        plugin = self._sensor_registry.get_or_create(f"ir-{robot_name}")
        return bool(plugin.read())

    def read_color_sensor_bytes(self) -> dict[str, int]:
        plugin = cast(Any, self._sensor_registry.get_or_create("color-left"))
        return plugin.read_rgb_bytes()

    async def record_external_event(self, payload: Any) -> None:
        await self._record_event(
            "EVENT", message="External event accepted", payload=payload
        )

    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        await self.event_store.append(event_type, **kwargs)


def _trigger_spec(trigger: AwaitTrigger) -> dict[str, Any]:
    if trigger.type == "http":
        return {"method": trigger.method, "path": trigger.path}
    if trigger.type == "kafka":
        return {"topic": trigger.topic}
    return {}
