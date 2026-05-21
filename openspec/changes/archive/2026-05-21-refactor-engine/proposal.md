# Refactor: explicit factory simulation model (simulated-factory)

## Why

The current `SimulationEngine` in `services/simulated-factory/simulated_factory/engine.py` concentrates most of the simulator's behavior in one runtime class. It currently owns preset progression, request-driven gates, sensor state and lifecycle, dobot and conveyor state, inventory polling, and event-facing coordination.

That makes the implementation harder to understand in terms of the factory being simulated. The service already exposes visibility and control concepts such as status, pending actions, sensor state, and event streams, but those concerns are not represented by clear simulation concepts internally. Instead, they are assembled indirectly from one broad engine object.

This proposal refactors the backend so the implementation reflects the abstract factory simulation more directly. The goal is not to add new API behavior, but to reshape the internals around explicit factory concepts so the existing visibility and control paths become easier to reason about, test, and extend.

## What changes

- Reorganize the backend around explicit simulation concepts rather than one monolithic engine implementation:
  - factory state / digital twin
  - process flow and preset progression
  - control points, gates, and pending actions
  - physical resources such as dobots, conveyor, sensors, and inventory-facing state
- Reduce `SimulationEngine` to a thin coordination façade that composes those concepts and preserves the current API-facing behavior.
- Extract sensor handling and lifecycle as part of the physical-resource model, instead of treating plugin mechanics as the main goal of the change.
- Update dependency wiring so the new simulation components are composed explicitly and can be tested independently.
- Keep event and publisher code as supporting infrastructure; only adjust it where necessary to fit the clearer coordinator boundary.
- Add developer documentation that explains the simulation model and how current visibility and control concerns map onto it.
- Add focused tests for the extracted simulation concepts, plus integration coverage for preset execution and request-gated flows.

## Scope / Non-goals

- This is an implementation refactor. Existing HTTP endpoints, payloads, and current preset behavior should remain unchanged.
- This proposal does not add new operator controls, new UI features, or new external API contracts.
- This proposal is not primarily a sensor-plugin overhaul, template effort, or publisher abstraction cleanup.
- This proposal does not change preset semantics or configuration format except for minimal internal compatibility work if required by the refactor.

## Impact

- Primary code targets:
  - `services/simulated-factory/simulated_factory/engine.py`
  - new internal modules that represent factory state, process flow, control points, and physical resources
  - `services/simulated-factory/simulated_factory/deps.py`
  - `services/simulated-factory/simulated_factory/models.py` and adjacent helper modules as needed
  - `services/simulated-factory/simulated_factory/sensors/*` where sensor handling must move behind clearer resource boundaries
  - tests under `services/simulated-factory/tests/`
  - developer-facing simulator documentation
- Other services:
  - no consumer-facing changes are expected for callers such as `dobot-control`

## Migration plan

1. Create design and tasks artifacts in this change (`design.md`, `tasks.md`) with the simulation-model boundaries as the primary design axis.
2. Extract a dedicated representation of factory state so runtime data is organized as a coherent simulation model rather than as engine-owned incidental state.
3. Extract process progression and preset execution into a dedicated component that advances the simulation model.
4. Extract request gating and pending-action handling into a dedicated control-point component.
5. Extract physical-resource handling for dobots, conveyor behavior, sensors, and inventory-facing state into dedicated components.
6. Recompose `SimulationEngine` as a thin coordinator / compatibility façade and update dependency wiring accordingly.
7. Add focused unit tests for the extracted concepts and integration tests that cover current preset and interactive flows.
8. Update developer documentation to explain the model and remove legacy helpers that no longer match the new structure.

## Risks & Mitigations

- The refactor could collapse back into a file split without a clearer model — Mitigation: treat explicit simulation concepts and a thin coordinator boundary as acceptance criteria, not optional implementation details.
- Behavioral regressions could appear in preset progression or request-driven gates — Mitigation: preserve the current API-facing behavior, keep incremental compatibility during migration, and run the existing preset / interactive test coverage.
- The new model could become too abstract to be useful — Mitigation: anchor each extracted concept to runtime responsibilities the simulator already exposes today, such as status, pending actions, sensor state, and preset advancement.

## Acceptance Criteria

- `SimulationEngine` is reduced to a coordination role and no longer directly owns most simulator logic.
- The simulator has identifiable, independently testable components for factory state, process progression, control points, and physical resources.
- Existing simulated-factory endpoints and current preset flows continue to behave as before.
- Developer documentation explains the simulation model and how visibility / control concerns map onto it.
- `services/simulated-factory` tests pass, including current preset and interactive behavior coverage.

## Next steps

- Create `design.md` and `tasks.md` in `openspec/changes/refactor-engine/` using the simulation model and coordinator boundary as the organizing structure.
- After review, implement the refactor incrementally behind the existing API surface.

## References

- Current engine implementation: `services/simulated-factory/simulated_factory/engine.py`
- Current dependency wiring: `services/simulated-factory/simulated_factory/deps.py`
- Current API surface: `services/simulated-factory/simulated_factory/api.py`
