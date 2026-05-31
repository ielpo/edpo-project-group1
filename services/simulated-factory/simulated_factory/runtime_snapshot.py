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
from simulated_factory.events import (
    ALL_EVENT_TYPES,
    EventStore,
    PROCESS_EVENT_TYPES,
    TYPE_LABELS,
    build_filter_param,
)
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
            activeGate=lifecycle.activeGate,
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

    def events_view(
        self,
        active_types: frozenset[str] | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        """View model for the events panel."""
        if active_types is None:
            active_types = PROCESS_EVENT_TYPES
        items, _ = self._event_store.list_events(
            page=1, page_size=limit, active_types=active_types
        )
        return self._events_panel_ctx(items, active_types)

    def _events_panel_ctx(
        self, events_items: list[dict[str, Any]], active_types: frozenset[str]
    ) -> dict[str, Any]:
        """Common event-panel context with precomputed chip toggle URLs."""
        type_chips = [
            {
                "type": t,
                "label": label,
                "active": t in active_types,
                "filter_param": build_filter_param(
                    active_types - {t} if t in active_types else active_types | {t}
                ),
            }
            for t, label in TYPE_LABELS
        ]
        preset_chips = [
            {
                "label": "All",
                "active": active_types == ALL_EVENT_TYPES,
                "filter_param": build_filter_param(ALL_EVENT_TYPES),
            },
            {
                "label": "Process",
                "active": active_types == PROCESS_EVENT_TYPES,
                "filter_param": build_filter_param(PROCESS_EVENT_TYPES),
            },
            {
                "label": "None",
                "active": not active_types,
                "filter_param": "",
            },
        ]
        return {
            "events": events_items,
            "active_types": active_types,
            "filter_param": build_filter_param(active_types),
            "type_chips": type_chips,
            "preset_chips": preset_chips,
        }

    def pending_view(self) -> dict[str, Any]:
        """View model for the pending actions panel."""
        return {"pending": self._engine.get_pending_actions()}

    # ------------------------------------------------------------------
    # Composed multi-panel snapshot (one coherent read cycle)
    # ------------------------------------------------------------------

    def all_panels(
        self, active_types: frozenset[str] | None = None
    ) -> dict[str, dict[str, Any]]:
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
            activeGate=lifecycle.activeGate,
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
        if active_types is None:
            active_types = PROCESS_EVENT_TYPES
        events_items, _ = self._event_store.list_events(
            page=1, page_size=30, active_types=active_types
        )
        pending = self._engine.get_pending_actions()

        return {
            "status": {"state": state_encoded},
            "presets": {"presets": presets, "state": state_encoded},
            "twin": {"state": state_encoded, "sensors": sensors, "inventory": inventory},
            "events": self._events_panel_ctx(events_items, active_types),
            "pending": {"pending": pending},
        }
