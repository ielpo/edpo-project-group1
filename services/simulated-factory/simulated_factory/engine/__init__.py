"""SimulationEngine facade — thin coordinator over process, control, and resource components.

This module preserves the full public API that api.py, deps.py, and tests expect.
All domain logic is delegated to ProcessRunner, ControlPointManager, and ResourceManager.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.events import EventStore
from simulated_factory.models import (
    DobotRuntimeState,
    InteractiveConfig,
    PendingAction,
    PresetDefinition,
    SensorConfig,
    SensorUpdateRequest,
    SimulationState,
    SimulationStatus,
    utc_now,
)
from simulated_factory.engine.runtime import (
    ControlState,
    FactoryState,
    PhysicalResources,
    ProcessState,
    SimulationRuntime,
)
from simulated_factory.engine.process_runner import ProcessRunner
from simulated_factory.engine.control_points import ControlPointManager
from simulated_factory.engine.resources import ResourceManager

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Compatibility facade — wires sub-components and exposes the public engine API."""

    def __init__(
        self,
        *,
        config_path: str,
        event_store: EventStore,
        distance_publisher: DistancePublisher,
        event_bridge: Any = None,
        inventory_url: str | None = None,
    ):
        self.event_store = event_store
        self.distance_publisher = distance_publisher
        self.event_bridge = event_bridge

        # Internal runtime model
        self._runtime = SimulationRuntime()

        # Resource manager (loads config, owns sensors/dobot/inventory)
        self._resource_mgr = ResourceManager(
            resources=self._runtime.resources,
            event_store=event_store,
            config_path=config_path,
            inventory_url=inventory_url,
        )

        # Load presets into process state
        self._runtime.process.presets = self._resource_mgr.get_presets()

        # Set current step getter for sensor reads that depend on step index
        self._resource_mgr.set_current_step_getter(
            lambda: self._runtime.process.current_step
        )

        # Initialize default dobot state
        self._runtime.resources.dobots = {
            "left": DobotRuntimeState(),
            "right": DobotRuntimeState(),
        }

        # Process runner (preset execution)
        self._process_runner = ProcessRunner(
            factory=self._runtime.factory,
            process=self._runtime.process,
            control=self._runtime.control,
            resources=self._runtime.resources,
            event_store=event_store,
            distance_publisher=distance_publisher,
        )

        # Control-point manager (gates, pending actions, commands)
        self._control_mgr = ControlPointManager(
            factory=self._runtime.factory,
            process=self._runtime.process,
            control=self._runtime.control,
            resources=self._runtime.resources,
            event_store=event_store,
        )

    # ------------------------------------------------------------------
    # Status snapshot (derives public model from internal runtime)
    # ------------------------------------------------------------------

    def get_status(self) -> SimulationState:
        rt = self._runtime
        state = SimulationState(
            id=rt.factory.run_id,
            status=rt.factory.status,
            currentPreset=rt.factory.current_preset,
            currentStep=rt.process.current_step,
            currentStepName=rt.process.current_step_name,
            timestamp=utc_now(),
            dobots={
                name: dobot.model_copy(deep=True)
                for name, dobot in rt.resources.dobots.items()
            },
            waitingForRequest=rt.control.waiting_for_request,
        )
        return state

    # ------------------------------------------------------------------
    # Preset handling (delegates to ProcessRunner)
    # ------------------------------------------------------------------

    def list_presets(self) -> list[dict[str, object]]:
        return self._process_runner.list_presets()

    async def run_preset(self, preset_name: str, speed: float = 1.0) -> str:
        # Prepare sensor map for the chosen preset
        preset = self._runtime.process.presets.get(preset_name)
        if preset is not None:
            self._runtime.resources.sensors = (
                self._resource_mgr.sensor_map_for_preset(preset)
            )
        return await self._process_runner.run_preset(preset_name, speed)

    async def stop(self) -> None:
        self._runtime.factory.stop_requested = True
        self._process_runner._clear_step_gate()
        await self.event_store.append(
            "STATE",
            message="Stop requested",
            payload={
                "runId": self._runtime.factory.run_id,
                "preset": self._runtime.factory.current_preset,
            },
        )

    async def reset(self) -> None:
        self._runtime.factory.stop_requested = True
        self._process_runner._clear_step_gate()
        task = self._runtime.factory.run_task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._runtime.reset()
        self._runtime.resources.sensors = (
            self._resource_mgr.sensor_map_for_preset(None)
        )
        await self.event_store.append(
            "STATE", message="Simulation reset", payload={"status": "reset"}
        )

    # ------------------------------------------------------------------
    # Request gate (delegates to ControlPointManager)
    # ------------------------------------------------------------------

    def fire_gate_if_matches(self, method: str, path: str) -> bool:
        """Fire gate if matches. Returns True if a gate was fired."""
        if not self._control_mgr.matches_gate(method, path):
            return False
        self._control_mgr.fire_gate_if_matches(method, path)
        return True

    def _matches_gate(self, method: str, path: str) -> bool:
        """Backward-compat: check if an incoming request matches the active gate."""
        return self._control_mgr.matches_gate(method, path)

    @property
    def _step_gate(self):
        """Backward-compat: direct access to step gate tuple."""
        return self._runtime.control.step_gate

    @_step_gate.setter
    def _step_gate(self, value):
        self._runtime.control.step_gate = value

    @property
    def _run_task(self):
        """Backward-compat: direct access to the run task."""
        return self._runtime.factory.run_task

    @_run_task.setter
    def _run_task(self, value):
        self._runtime.factory.run_task = value

    # ------------------------------------------------------------------
    # Command handling (delegates to ControlPointManager)
    # ------------------------------------------------------------------

    async def handle_dobot_commands(
        self, robot_name: str, payload: Any
    ) -> dict[str, Any]:
        return await self._control_mgr.handle_dobot_commands(robot_name, payload)

    async def resolve_action(
        self, action_id: str, outcome: str, reason: str | None = None
    ) -> PendingAction:
        return await self._control_mgr.resolve_action(action_id, outcome, reason)

    def get_pending_actions(self) -> list[dict[str, Any]]:
        return self._control_mgr.get_pending_actions()

    def get_interactive_config(self) -> InteractiveConfig:
        return self._control_mgr.get_interactive_config()

    def set_interactive_config(self, config: InteractiveConfig) -> InteractiveConfig:
        return self._control_mgr.set_interactive_config(config)

    # ------------------------------------------------------------------
    # Sensor management (delegates to ResourceManager)
    # ------------------------------------------------------------------

    def get_sensor_configs(self) -> list[SensorConfig]:
        return self._resource_mgr.get_sensor_configs()

    async def update_sensor(
        self, sensor_id: str, update: SensorUpdateRequest
    ) -> SensorConfig:
        return await self._resource_mgr.update_sensor(sensor_id, update)

    def read_color(self, robot_name: str) -> tuple[str, list[int]]:
        return self._resource_mgr.read_color(robot_name)

    def read_ir(self, robot_name: str) -> bool:
        return self._resource_mgr.read_ir(robot_name)

    def read_color_sensor_bytes(self) -> dict[str, int]:
        return self._resource_mgr.read_color_sensor_bytes()

    # ------------------------------------------------------------------
    # Dobot state (delegates to ResourceManager)
    # ------------------------------------------------------------------

    def get_dobot_state(self, robot_name: str) -> DobotRuntimeState:
        return self._resource_mgr.get_dobot_state(robot_name)

    # ------------------------------------------------------------------
    # Inventory (delegates to ResourceManager)
    # ------------------------------------------------------------------

    def get_inventory_cache(self) -> dict:
        return self._resource_mgr.get_inventory_cache()

    def start_inventory_poller(self) -> None:
        self._resource_mgr.start_inventory_poller()

    async def stop_inventory_poller(self) -> None:
        await self._resource_mgr.stop_inventory_poller()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def record_external_event(self, payload: Any) -> None:
        await self.event_store.append(
            "EVENT", message="External event accepted", payload=payload
        )

    # ------------------------------------------------------------------
    # Backward-compat properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> "_MutableStateProxy":
        """Legacy property — some tests access engine.state directly and mutate it."""
        return _MutableStateProxy(self._runtime)

    @state.setter
    def state(self, value: SimulationState) -> None:
        """Allow full replacement of state (used by reset path)."""
        self._runtime.factory.run_id = value.id
        self._runtime.factory.status = value.status
        self._runtime.factory.current_preset = value.currentPreset
        self._runtime.process.current_step = value.currentStep
        self._runtime.process.current_step_name = value.currentStepName
        self._runtime.control.waiting_for_request = value.waitingForRequest
        self._runtime.resources.dobots = {
            name: dobot.model_copy(deep=True)
            for name, dobot in value.dobots.items()
        }

    @property
    def sensors(self) -> dict:
        return self._runtime.resources.sensors

    @sensors.setter
    def sensors(self, value: dict) -> None:
        self._runtime.resources.sensors = value

    @property
    def presets(self) -> dict[str, PresetDefinition]:
        return self._runtime.process.presets

    @property
    def interactive_config(self) -> InteractiveConfig:
        return self._runtime.control.interactive_config

    @interactive_config.setter
    def interactive_config(self, value: InteractiveConfig) -> None:
        self._runtime.control.interactive_config = value

    @property
    def _inventory_cache(self):
        """Backward-compat: direct access to inventory cache."""
        return self._runtime.resources.inventory_cache

    @_inventory_cache.setter
    def _inventory_cache(self, value):
        self._runtime.resources.inventory_cache = value


class _MutableStateProxy:
    """Proxy object that exposes SimulationState-like attributes backed by runtime."""

    def __init__(self, runtime: SimulationRuntime):
        object.__setattr__(self, "_rt", runtime)

    @property
    def id(self) -> str:
        return self._rt.factory.run_id

    @id.setter
    def id(self, value: str) -> None:
        self._rt.factory.run_id = value

    @property
    def status(self) -> SimulationStatus:
        return self._rt.factory.status

    @status.setter
    def status(self, value: SimulationStatus) -> None:
        self._rt.factory.status = value

    @property
    def currentPreset(self) -> str | None:
        return self._rt.factory.current_preset

    @currentPreset.setter
    def currentPreset(self, value: str | None) -> None:
        self._rt.factory.current_preset = value

    @property
    def currentStep(self) -> int:
        return self._rt.process.current_step

    @currentStep.setter
    def currentStep(self, value: int) -> None:
        self._rt.process.current_step = value

    @property
    def currentStepName(self) -> str | None:
        return self._rt.process.current_step_name

    @currentStepName.setter
    def currentStepName(self, value: str | None) -> None:
        self._rt.process.current_step_name = value

    @property
    def timestamp(self):
        return utc_now()

    @timestamp.setter
    def timestamp(self, value) -> None:
        pass  # not tracked internally

    @property
    def dobots(self) -> dict[str, DobotRuntimeState]:
        return self._rt.resources.dobots

    @dobots.setter
    def dobots(self, value: dict[str, DobotRuntimeState]) -> None:
        self._rt.resources.dobots = value

    @property
    def waitingForRequest(self):
        return self._rt.control.waiting_for_request

    @waitingForRequest.setter
    def waitingForRequest(self, value) -> None:
        self._rt.control.waiting_for_request = value

    def model_copy(self, deep: bool = False) -> SimulationState:
        return SimulationState(
            id=self._rt.factory.run_id,
            status=self._rt.factory.status,
            currentPreset=self._rt.factory.current_preset,
            currentStep=self._rt.process.current_step,
            currentStepName=self._rt.process.current_step_name,
            timestamp=utc_now(),
            dobots={
                name: dobot.model_copy(deep=True)
                for name, dobot in self._rt.resources.dobots.items()
            },
            waitingForRequest=self._rt.control.waiting_for_request,
        )
