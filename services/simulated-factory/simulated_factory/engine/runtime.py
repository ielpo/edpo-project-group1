"""Internal mutable runtime model for the factory simulation.

These dataclasses hold the mutable simulation state grouped by domain:
- FactoryState: top-level run lifecycle
- ProcessState: preset progression and step sequencing
- ControlState: request gates and pending actions
- PhysicalResources: sensors, dobots, inventory cache

Public API snapshots (Pydantic models in models.py) are derived from this
runtime model; they are never mutated directly by API handlers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from simulated_factory.models import (
    AwaitRequest,
    DobotRuntimeState,
    InteractiveConfig,
    PendingAction,
    PresetDefinition,
    PresetStep,
    SimulationStatus,
    utc_now,
)
from simulated_factory.sensors.base import BaseSensor


@dataclass
class FactoryState:
    """Top-level simulation lifecycle state."""

    run_id: str = "run-0000"
    status: SimulationStatus = SimulationStatus.IDLE
    current_preset: str | None = None
    run_counter: int = 0
    stop_requested: bool = False
    run_task: asyncio.Task | None = field(default=None, repr=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


@dataclass
class ProcessState:
    """Preset progression and step sequencing."""

    current_step: int = 0
    current_step_name: str | None = None
    presets: dict[str, PresetDefinition] = field(default_factory=dict)


@dataclass
class ControlState:
    """Request gates, pending actions, and interactive config."""

    step_gate: tuple[AwaitRequest, asyncio.Event, PresetStep] | None = None
    waiting_for_request: AwaitRequest | None = None
    interactive_config: InteractiveConfig = field(default_factory=InteractiveConfig)
    pending: dict[str, PendingAction] = field(default_factory=dict)
    pending_counter: int = 0


@dataclass
class PhysicalResources:
    """Sensors, dobot state, and inventory cache."""

    default_sensors: dict[str, BaseSensor] = field(default_factory=dict)
    sensors: dict[str, BaseSensor] = field(default_factory=dict)
    dobots: dict[str, DobotRuntimeState] = field(default_factory=dict)
    inventory_cache: dict | None = None
    inventory_poll_task: asyncio.Task | None = field(default=None, repr=False)


@dataclass
class SimulationRuntime:
    """Aggregates all mutable runtime state for the simulation."""

    factory: FactoryState = field(default_factory=FactoryState)
    process: ProcessState = field(default_factory=ProcessState)
    control: ControlState = field(default_factory=ControlState)
    resources: PhysicalResources = field(default_factory=PhysicalResources)

    def reset(self) -> None:
        """Reset all runtime state to initial values."""
        self.factory.run_id = "run-0000"
        self.factory.status = SimulationStatus.IDLE
        self.factory.current_preset = None
        self.factory.stop_requested = False
        self.factory.run_task = None

        self.process.current_step = 0
        self.process.current_step_name = None

        self.control.step_gate = None
        self.control.waiting_for_request = None
        self.control.pending.clear()
        self.control.pending_counter = 0

        self.resources.dobots = {
            "left": DobotRuntimeState(),
            "right": DobotRuntimeState(),
        }
