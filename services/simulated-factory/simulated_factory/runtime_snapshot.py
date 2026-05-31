"""Data-only read composer for the simulated-factory UI.

Assembles view models for /api/status, fragment endpoints, and SSE updates
from one coherent read cycle. Does NOT render HTML — that stays in api.py
and Jinja templates.
"""

from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder

from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.adapters.inventory_poller import InventoryPoller
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventStore
from simulated_factory.models import SimulationState
from simulated_factory.sensor_registry import SensorRegistry


class RuntimeSnapshot:
    """Composes read-only view models from multiple ownership-backed sources."""

    def __init__(
        self,
        *,
        engine: SimulationEngine,
        sensor_registry: SensorRegistry,
        actuator_registry: ActuatorRegistry,
        inventory_poller: InventoryPoller,
        event_store: EventStore,
    ) -> None:
        self._engine = engine
        self._sensor_registry = sensor_registry
        self._actuator_registry = actuator_registry
        self._inventory_poller = inventory_poller
        self._event_store = event_store

    # ------------------------------------------------------------------
    # Individual panel view models
    # ------------------------------------------------------------------

    def status_view(self) -> dict[str, Any]:
        """Public /api/status payload — lifecycle + actuator state."""
        lifecycle = self._engine.get_status()
        dobots = self._actuator_registry.all_states()
        state = SimulationState(
            id=lifecycle.id,
            status=lifecycle.status,
            currentPreset=lifecycle.currentPreset,
            currentStep=lifecycle.currentStep,
            currentStepName=lifecycle.currentStepName,
            timestamp=lifecycle.timestamp,
            dobots=dobots,
            waitingForRequest=lifecycle.waitingForRequest,
        )
        return jsonable_encoder(state)

    def presets_view(self) -> dict[str, Any]:
        """View model for the presets panel."""
        presets = [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in self._sensor_registry.get_presets().values()
        ]
        return {
            "presets": presets,
            "state": self.status_view(),
        }

    def twin_view(self) -> dict[str, Any]:
        """View model for the twin panel."""
        return {
            "state": self.status_view(),
            "sensors": jsonable_encoder(self._sensor_registry.configs()),
            "inventory": self._inventory_poller.get_cache(),
        }

    def events_view(self, filter_mode: str = "full", limit: int = 30) -> dict[str, Any]:
        """View model for the events panel."""
        items, _ = self._event_store.list_events(
            page=1, page_size=limit, filter_mode=filter_mode
        )
        return {
            "events": items,
            "filter_mode": filter_mode,
        }

    def pending_view(self) -> dict[str, Any]:
        """View model for the pending actions panel."""
        return {"pending": self._engine.get_pending_actions()}

    # ------------------------------------------------------------------
    # Composed multi-panel snapshot (one coherent read cycle)
    # ------------------------------------------------------------------

    def all_panels(self, filter_mode: str = "full") -> dict[str, dict[str, Any]]:
        """Derive all panel data from one base read cycle.

        Captures shared state once and derives every panel from it so that
        a single SSE update event is internally consistent.
        """
        # One coherent base read
        lifecycle = self._engine.get_status()
        dobots = self._actuator_registry.all_states()
        state = SimulationState(
            id=lifecycle.id,
            status=lifecycle.status,
            currentPreset=lifecycle.currentPreset,
            currentStep=lifecycle.currentStep,
            currentStepName=lifecycle.currentStepName,
            timestamp=lifecycle.timestamp,
            dobots=dobots,
            waitingForRequest=lifecycle.waitingForRequest,
        )
        state_encoded = jsonable_encoder(state)

        sensors = jsonable_encoder(self._sensor_registry.configs())
        inventory = self._inventory_poller.get_cache()
        presets = [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in self._sensor_registry.get_presets().values()
        ]
        events_items, _ = self._event_store.list_events(
            page=1, page_size=30, filter_mode=filter_mode
        )
        pending = self._engine.get_pending_actions()

        return {
            "status": {"state": state_encoded},
            "presets": {"presets": presets, "state": state_encoded},
            "twin": {"state": state_encoded, "sensors": sensors, "inventory": inventory},
            "events": {"events": events_items, "filter_mode": filter_mode},
            "pending": {"pending": pending},
        }
