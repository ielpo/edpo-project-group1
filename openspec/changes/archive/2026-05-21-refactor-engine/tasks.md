# Implementation Tasks

## 1. Simulation model boundary

- [x] 1.1 Introduce an internal runtime model for factory state, process state, control state, and physical resources.
- [x] 1.2 Extract preset progression into a dedicated process runner that owns step sequencing and step-side effects.
- [x] 1.3 Extract request-gated control and pending-action handling into a dedicated control-point manager.

## 2. Resource layer and compatibility

- [x] 2.1 Extract sensor instantiation, clone/fallback behavior, and runtime updates into a resource manager.
- [x] 2.2 Preserve explicit `type` support while keeping prefix-based inference for existing sensor configs.
- [x] 2.3 Keep inventory polling as a cached, non-blocking background concern inside the resource layer.
- [x] 2.4 Move dobot state mutations behind the new resource layer without changing command semantics.

## 3. Facade and wiring

- [x] 3.1 Recompose `SimulationEngine` as a thin facade over the new components.
- [x] 3.2 Update `deps.py` wiring to build the new simulation components explicitly.
- [x] 3.3 Keep `api.py` endpoint behavior unchanged while delegating to the refactored engine.

## 4. Tests and docs

- [x] 4.1 Add unit tests for the process runner, control points, and resource layer.
- [x] 4.2 Add integration coverage for preset execution, request gates, sensor updates, and command handling.
- [x] 4.3 Update developer documentation to explain the factory simulation model and component boundaries.
- [x] 4.4 Run the simulated-factory test suite and fix any regressions introduced by the refactor.
