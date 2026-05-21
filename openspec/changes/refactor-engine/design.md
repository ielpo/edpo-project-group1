# Design: explicit factory simulation model for simulated-factory

## Context

`SimulationEngine` currently concentrates nearly all runtime behavior for the simulated-factory service. It owns preset progression, request-gated steps, pending action handling, sensor instantiation and updates, dobot state mutation, distance publishing, event emission, and inventory polling. The FastAPI layer already exposes a narrower public surface through run/stop/reset, sensor reads and updates, request-driven gates, pending action resolution, and event streaming.

The implementation should therefore mirror the simulation domains that the service already presents to callers: factory state, process progression, control points, and physical resources. The goal is not to add new user-facing behavior. The goal is to reorganize the internals so the current visibility and control paths are backed by explicit simulation concepts instead of being assembled indirectly from one broad runtime class.

## Goals / Non-Goals

**Goals:**
- Keep the existing HTTP, SSE, and preset behavior unchanged for callers.
- Make factory state, process flow, control points, and physical resources explicit in the implementation.
- Reduce `SimulationEngine` to a thin coordinator and compatibility facade.
- Preserve sensor configuration compatibility, including prefix-based inference and optional explicit `type`.
- Keep inventory polling, event logging, and publishing available, but move them behind clearer component boundaries.
- Make the core simulation responsibilities independently testable.

**Non-Goals:**
- No new operator-facing features or UI redesign.
- No change to the public API contract.
- No change to preset semantics or request-gating semantics.
- No sensor hot-reload.
- No publisher rewrite beyond the minimum wiring needed for the new boundary.

## Decisions

### 1. Keep public models stable, introduce an internal runtime model

`SimulationState`, `PresetDefinition`, `PresetStep`, `PendingAction`, and `SensorConfig` remain the public data models used by the API and tests. The refactor introduces an internal mutable runtime model that groups the simulation into the following areas:

- factory state / digital twin
- process state
- control state
- physical resource state

The internal model is owned by the new simulation components. Public methods continue returning deep copies of the public snapshot models.

Why: this preserves compatibility while separating mutable runtime state from API-facing response objects. It also makes it easier to test behavior without mutating the same object graph that the API serializes.

### 2. Split behavior by simulation responsibility, not by generic utility

The design should introduce a small number of domain-focused components instead of many helper modules with overlapping responsibilities:

- `ProcessRunner` owns preset loading, step advancement, and sequencing of step side effects.
- `ControlPointManager` owns request-gated behavior, pending actions, command interception, and resolution.
- `ResourceManager` owns sensors, dobot state, inventory cache, and resource-specific reads and updates.
- `SimulationEngine` becomes the facade that wires these pieces together and exposes the current public methods.

This is a structural boundary, not a public API change. The existing methods on `SimulationEngine` stay in place and delegate into the new components.

Why: the current code groups unrelated concerns by convenience. A responsibility-based split makes each component align with one part of the simulation model, which is easier to reason about and test.

### 3. Preserve request-gated behavior and middleware ordering

The existing middleware behavior in `api.py` should remain intact: incoming requests still call `engine.fire_gate_if_matches(method, path)` before the handler runs. That timing matters because a gated step must observe the updated state before the request completes.

Gate matching should continue to use the existing path-pattern semantics, including the current request-template matching behavior. When a gate times out, the current behavior should remain: apply the step side effects, clear the waiting state, and record the timeout event.

Why: request-gated preset steps are already part of the service contract. The refactor should clarify the implementation without changing when or how gates are resolved.

### 4. Keep sensor compatibility while moving sensor ownership behind the resource layer

The built-in sensor plugins stay under `simulated_factory/sensors/`, and `BaseSensor` remains the canonical interface. The resource layer should own:

- sensor instantiation
- clone/fallback behavior
- sensor override application
- runtime reads and updates
- sensor configuration snapshots

The loader should continue supporting prefix-based type inference for existing configs and also accept explicit `type` when present.

Why: this keeps existing `config.yml` files working while making sensor handling part of the physical-resource model instead of a special case in the engine.

### 5. Keep inventory polling and publishing as supporting infrastructure

Inventory polling should remain a background task with a cached snapshot because the UI and fragments render inventory synchronously. Distance publishing and other side effects should remain adapter concerns; the new design only changes who triggers them.

Why: these are effects of simulation progression, not the simulation model itself. Pulling them into the domain model would add complexity without improving the factory abstraction.

### 6. Reuse the existing event store as the observation layer

The current `EventStore` already powers the UI and test assertions, so the design should not introduce a second event system. The new components should continue recording the existing event types, including STATE, COMMAND, PENDING_ACTION, ACTION_RESOLVED, SENSOR_REQUEST, REST, and MQTT.

Why: the event store already provides the visibility surface the service needs. Replacing it would add migration risk without improving the design boundary.

### 7. Keep `SimulationEngine` as the compatibility facade during migration

The public engine class should remain the entry point used by `api.py`, `deps.py`, and the tests. It should own the lifecycle methods that coordinate the subcomponents (`run_preset`, `stop`, `reset`, inventory poller startup/shutdown), but it should not directly implement the core simulation logic once the extraction is complete.

Why: this allows the refactor to land incrementally without forcing consumers to change their imports or behavior.

## Migration Plan

1. Introduce the internal runtime model and move state reads and writes behind it without changing public methods.
2. Extract the process runner first, because it defines preset advancement and step sequencing.
3. Extract the control-point manager next, because request-gated behavior and pending actions are the most coupled interactive paths.
4. Extract the resource layer for sensors, dobot runtime state, and inventory polling.
5. Recompose `SimulationEngine` as a thin facade over those components and update dependency wiring in `deps.py`.
6. Keep `api.py` unchanged except for any wiring simplifications needed to call the same public engine methods.
7. Add focused unit tests for each extracted component and a small set of integration tests that exercise current preset and gated flows.
8. Update developer documentation to explain the new simulation model and how the existing visibility and control endpoints map onto it.

## Risks / Trade-offs

- [More modules can make the code feel abstract at first] -> Mitigation: keep `SimulationEngine` as the single public entry point and keep the number of new concepts limited to the four core simulation domains.
- [Mutable internal state can drift away from the public snapshot model] -> Mitigation: derive public snapshots from the runtime model in one place and add tests for serialization and status transitions.
- [Sensor compatibility regressions] -> Mitigation: preserve prefix inference, accept explicit `type`, and cover the existing built-in sensor cases with tests.
- [Gate timing changes could alter preset behavior] -> Mitigation: keep the middleware ordering unchanged and add request-driven integration coverage for gated steps.
- [Inventory polling and publishing can still fail independently] -> Mitigation: keep both best-effort and non-blocking, with failures isolated from the main simulation loop.

## Open Questions

- Should the internal runtime model live under `simulated_factory/engine/` as domain modules, or in separate adjacent packages? Recommendation: keep it under `engine/` so the new boundaries remain close to the facade and easier to navigate.
- Should the mutable runtime model use dataclasses while the public snapshots stay as Pydantic models? Recommendation: yes, because it keeps mutation simple internally while preserving the current response models.
- Should `type` inference remain indefinitely for backward compatibility, or should it become a migration-only path later? Recommendation: keep inference for existing configs and prefer explicit `type` for new configs.
