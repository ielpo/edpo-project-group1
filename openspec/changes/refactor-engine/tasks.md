# Implementation Tasks

## 1. Simulation model boundary

- [ ] 1.1 Introduce an internal runtime model for factory state, process state, control state, and physical resources.
- [ ] 1.2 Extract preset progression into a dedicated process runner that owns step sequencing and step-side effects.
- [ ] 1.3 Extract request-gated control and pending-action handling into a dedicated control-point manager.

## 2. Resource layer and compatibility

- [ ] 2.1 Extract sensor instantiation, clone/fallback behavior, and runtime updates into a resource manager.
- [ ] 2.2 Preserve explicit `type` support while keeping prefix-based inference for existing sensor configs.
- [ ] 2.3 Keep inventory polling as a cached, non-blocking background concern inside the resource layer.
- [ ] 2.4 Move dobot state mutations behind the new resource layer without changing command semantics.

## 3. Facade and wiring

- [ ] 3.1 Recompose `SimulationEngine` as a thin facade over the new components.
- [ ] 3.2 Update `deps.py` wiring to build the new simulation components explicitly.
- [ ] 3.3 Keep `api.py` endpoint behavior unchanged while delegating to the refactored engine.

## 4. Tests and docs

- [ ] 4.1 Add unit tests for the process runner, control points, and resource layer.
- [ ] 4.2 Add integration coverage for preset execution, request gates, sensor updates, and command handling.
- [ ] 4.3 Update developer documentation to explain the factory simulation model and component boundaries.
- [ ] 4.4 Run the simulated-factory test suite and fix any regressions introduced by the refactor.
