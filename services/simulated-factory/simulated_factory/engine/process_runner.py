"""Process runner: owns preset loading, step advancement, and step side-effects."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from simulated_factory.models import (
    PresetDefinition,
    PresetStep,
    SimulationStatus,
    utc_now,
)
from simulated_factory.engine.runtime import (
    ControlState,
    FactoryState,
    PhysicalResources,
    ProcessState,
)

if TYPE_CHECKING:
    from simulated_factory.adapters.distance_publisher import DistancePublisher
    from simulated_factory.events import EventStore

logger = logging.getLogger(__name__)


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


class ProcessRunner:
    """Owns preset step sequencing and step side-effects."""

    def __init__(
        self,
        *,
        factory: FactoryState,
        process: ProcessState,
        control: ControlState,
        resources: PhysicalResources,
        event_store: EventStore,
        distance_publisher: DistancePublisher,
    ):
        self._factory = factory
        self._process = process
        self._control = control
        self._resources = resources
        self._event_store = event_store
        self._distance_publisher = distance_publisher

    def list_presets(self) -> list[dict[str, object]]:
        return [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in self._process.presets.values()
        ]

    async def run_preset(self, preset_name: str, speed: float = 1.0) -> str:
        preset = self._process.presets.get(preset_name)
        if preset is None:
            raise KeyError(preset_name)

        async with self._factory.lock:
            if self._factory.run_task and not self._factory.run_task.done():
                raise RuntimeError("simulation already running")

            self._factory.run_counter += 1
            run_id = f"run-{self._factory.run_counter:04d}"
            self._factory.stop_requested = False
            self._factory.run_id = run_id
            self._factory.status = SimulationStatus.RUNNING
            self._factory.current_preset = preset_name

            self._process.current_step = 0
            self._process.current_step_name = None

            from simulated_factory.models import InteractiveConfig

            self._control.interactive_config = InteractiveConfig()

            await self._record_event(
                "STATE",
                message=f"Started preset {preset_name}",
                payload={"runId": run_id, "preset": preset_name},
            )

            self._factory.run_task = asyncio.create_task(
                self._execute_preset(preset, speed)
            )
            return run_id

    async def _execute_preset(
        self, preset: PresetDefinition, speed: float = 1.0
    ) -> None:
        try:
            for index, step in enumerate(preset.steps, start=1):
                if self._factory.stop_requested:
                    self._factory.status = SimulationStatus.STOPPED
                    await self._record_event(
                        "STATE",
                        message=f"Preset {preset.name} stopped",
                        payload={
                            "runId": self._factory.run_id,
                            "preset": preset.name,
                        },
                    )
                    return

                self._process.current_step = index
                self._process.current_step_name = step.name
                await self._record_event(
                    "STATE",
                    message=step.note or f"Executing step {step.name}",
                    payload={
                        "runId": self._factory.run_id,
                        "preset": preset.name,
                        "step": index,
                        "stepName": step.name,
                    },
                )

                if step.awaitRequest is not None:
                    await self._await_step_gate(step, speed)
                else:
                    self._apply_step_side_effects_sync(step)
                    await self._publish_distance_if_needed(step)
                    delay = step.delayMs / 1000.0
                    if speed > 0:
                        delay /= speed
                    await asyncio.sleep(delay)

            self._factory.status = SimulationStatus.IDLE
            await self._record_event(
                "STATE",
                message=f"Preset {preset.name} completed",
                payload={
                    "runId": self._factory.run_id,
                    "preset": preset.name,
                },
            )
        except asyncio.CancelledError:
            self._factory.status = SimulationStatus.STOPPED
            raise
        finally:
            self._factory.stop_requested = False
            self._clear_step_gate()
            from simulated_factory.models import InteractiveConfig

            self._control.interactive_config = InteractiveConfig(
                intercepted=set(_DEFAULT_INTERCEPTED)
            )

    async def _await_step_gate(self, step: PresetStep, speed: float = 1.0) -> None:
        assert step.awaitRequest is not None
        event = asyncio.Event()
        self._control.step_gate = (step.awaitRequest, event, step)
        self._control.waiting_for_request = step.awaitRequest.model_copy()
        timeout = step.delayMs / 1000.0
        if speed > 0:
            timeout /= speed
        fired = False
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            fired = True
        except asyncio.TimeoutError:
            self._apply_step_side_effects_sync(step)
            await self._publish_distance_if_needed(step)
            await self._record_event(
                "STATE",
                message=f"Step {step.name} gate timed out",
                payload={
                    "runId": self._factory.run_id,
                    "preset": self._factory.current_preset,
                    "step": self._process.current_step,
                    "stepName": step.name,
                    "gateTimedOut": True,
                },
            )
        finally:
            current = self._control.step_gate
            if current is not None and current[1] is event:
                self._control.step_gate = None
            self._control.waiting_for_request = None
        # If gate fired normally, publish distance (sensor updates were
        # already applied synchronously by fire_gate_if_matches).
        if fired:
            await self._publish_distance_if_needed(step)

    def _clear_step_gate(self) -> None:
        gate = self._control.step_gate
        if gate is not None:
            _, event, _ = gate
            event.set()
            self._control.step_gate = None
        self._control.waiting_for_request = None

    def _apply_step_side_effects_sync(self, step: PresetStep) -> None:
        """Apply sensor updates from a preset step (synchronous)."""
        for sensor_id, value in step.sensorUpdates.items():
            if sensor_id not in self._resources.sensors:
                from simulated_factory.engine.resources import ResourceManager

                # Lazy import to avoid circular; in practice the resource
                # manager should have been set up before we get here.
                pass
            plugin = self._resources.sensors.get(sensor_id)
            if plugin is None:
                continue
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

    async def _publish_distance_if_needed(self, step: PresetStep) -> None:
        if step.publishDistance is not None:
            # Find the first distance sensor available
            distance_plugin = None
            for sid, plugin in self._resources.sensors.items():
                if sid.startswith("distance-"):
                    distance_plugin = plugin
                    break
            if distance_plugin:
                to_sensor_cfg = getattr(distance_plugin, "to_sensor_config", None)
                if callable(to_sensor_cfg):
                    cfg = to_sensor_cfg()
                else:
                    cfg = getattr(distance_plugin, "_cfg", None)
                    if cfg is not None and hasattr(cfg, "model_copy"):
                        cfg = cfg.model_copy(deep=True)
                await self._distance_publisher.publish(
                    cfg, float(step.publishDistance)
                )

    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        await self._event_store.append(event_type, **kwargs)
