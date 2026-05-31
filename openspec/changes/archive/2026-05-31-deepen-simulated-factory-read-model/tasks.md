## 1. Rewire state owners and constructor surfaces

- [x] 1.1 Move `SensorRegistry` and `ActuatorRegistry` construction into `deps.py` and inject the shared instances into `SimulationEngine`
- [x] 1.2 Deepen `ActuatorRegistry` into the sole live dobot owner with explicit command-apply, state-query, and reset operations while keeping the existing name
- [x] 1.3 Remove engine constructor and reset plumbing that no longer matches ownership (`config_path`, `inventory_poller`, `event_bridge`)

## 2. Narrow the engine interface

- [x] 2.1 Split the engine's lifecycle-only status model from the public `GET /api/status` payload
- [x] 2.2 Remove engine pass-through reads for preset catalog, sensor configs, dobot runtime state, and inventory cache
- [x] 2.3 Keep lifecycle-owned reads plus write-side sensor mutation on the engine: status, gating/preset control, pending actions, interactive config, `update_sensor`, and step-aware color/IR reads

## 3. Add a runtime snapshot for composed reads

- [x] 3.1 Create `runtime_snapshot.py` as a data-only read composer for status, presets, twin, events, and pending views
- [x] 3.2 Make `runtime_snapshot.all_panels(filter_mode)` derive every panel from one coherent read cycle, and route `GET /api/status`, fragment handlers, and `GET /sse/status` through that shared path
- [x] 3.3 Keep HTML rendering in `api.py` and Jinja templates rather than in the snapshot module

## 4. Direct-route single-owner endpoints and test seams

- [x] 4.1 Update `GET /api/presets` and `GET /api/config/sensors` to read `SensorRegistry` directly, mapping raw preset definitions to the existing response shape outside the registry
- [x] 4.2 Update `GET /api/inventory` to read `InventoryPoller` directly and `GET /api/dobot/{name}/state` to read `ActuatorRegistry` directly
- [x] 4.3 Expose `sensor_registry`, `actuator_registry`, `inventory_poller`, and `runtime_snapshot` on `app.state` so API tests stop reaching through private engine fields

## 5. Verify behavior at the right seam

- [x] 5.1 Add focused unit tests for `ActuatorRegistry` and `runtime_snapshot`
- [x] 5.2 Update API, fragment, and SSE tests to use the new app wiring seam while keeping twin badge/grouping semantics covered at the fragment-template level
- [x] 5.3 Run the simulated-factory test suite and confirm public payloads plus htmx/SSE update flows do not regress