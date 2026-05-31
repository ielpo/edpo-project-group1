## Why

The simulated-factory HTTP module currently reaches runtime state through the engine even when the engine does not own that state. Inventory cache, sensor configuration, preset catalog, and dobot runtime state are exposed through shallow pass-through methods, while `/api/status`, the UI fragments, and the SSE path rebuild related panel data from scattered calls. This makes the read side hard to trace, weakens locality, and makes it easy for UI updates to mix independently assembled state.

## What Changes

- Rewire `SensorRegistry`, `ActuatorRegistry`, and `InventoryPoller` as explicit ownership-backed read sources built in `deps.py`, then inject them into the engine and HTTP wiring.
- Deepen `ActuatorRegistry` in place as the sole live dobot-state owner and keep `SimulationEngine` focused on lifecycle state, gating, pending actions, command handling, and sensor writes.
- Introduce a data-only `runtime_snapshot.py` module for composed reads so `GET /api/status`, the fragment endpoints, and `GET /sse/status` share one coherent snapshot path per update cycle.
- Keep single-owner endpoints direct in `api.py`: presets and sensor configs read from `SensorRegistry`, inventory reads from `InventoryPoller`, and dobot state reads from `ActuatorRegistry`.
- Split the engine's internal lifecycle status model from the public `/api/status` payload, preserve existing response shapes, and remove dead engine constructor plumbing that no longer matches ownership (`config_path`, `inventory_poller`, `event_bridge`).
- Add focused snapshot and wiring tests, while keeping twin fragment tests responsible for template-only badge/grouping semantics that remain in Jinja.

## Capabilities

### New Capabilities
- `simulated-factory-read-model`: Defines the in-process read model for direct ownership-backed reads, a lifecycle-only engine status seam, and the shared runtime snapshot used by the HTTP module for composed views.

### Modified Capabilities
- `simulator-htmx-frontend`: `GET /api/status`, fragment endpoints, and `GET /sse/status` use one shared runtime snapshot source so each update cycle renders a coherent UI state without changing the public simulator contract.

## Impact

- `services/simulated-factory/simulated_factory/api.py`
- `services/simulated-factory/simulated_factory/deps.py`
- `services/simulated-factory/simulated_factory/engine.py`
- `services/simulated-factory/simulated_factory/models.py`
- `services/simulated-factory/simulated_factory/runtime_snapshot.py`
- `services/simulated-factory/simulated_factory/actuator_registry.py`
- `services/simulated-factory/simulated_factory/sensor_registry.py`
- `services/simulated-factory/simulated_factory/adapters/inventory_poller.py`
- `services/simulated-factory/tests/`
- No external API or protocol changes