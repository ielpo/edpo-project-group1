# Tasks: Implement simulated factory service (aligned with design)

1. Scaffold simulator repository
   - Create `services/simulated-factory/` with a minimal FastAPI app, `pyproject.toml`, and `Dockerfile`.
   - Add `presets.yml` with at least a `happy-path` preset and example sensor configs.
   - Acceptance: `GET /api/status` returns `{ "status": "idle" }` and `GET /api/presets` lists `happy-path`.
   - Estimate: 0.5 day

2. Define simulator API contract
   - Add `services/simulated-factory/api.md` documenting the minimal, versioned REST contract described in `design.md` (commands endpoint, sensor reads, state, events) with payload examples.
   - Acceptance: contract file exists and is referenced by the adapter and README.
   - Estimate: 0.25 day

3. Add simulator config to `dobot-control`
   - Extend `services/dobot-control/config.yml` with an optional `simulator` section: `url`, `broker` (optional), and timeouts.
   - Acceptance: `dobot-control` can be started with `--simulation` and reads simulator config from `config.yml` or `SIMULATOR_URL` env var.
   - Estimate: 0.25 day

4. Implement `simulator_client.py` and DobotFake integration
   - Define a small client interface used by `DobotFake` to POST commands and GET sensor values from the simulator. Include non-blocking/timeout behaviour and clear logging.
   - Update `DobotFake` to use `simulator_client` when simulator config is present: forward actuator commands and query sensors as needed.
   - Acceptance: `DobotFake` forwards movement and conveyor commands to the simulator and returns simulator-provided sensor values for `read_color`/`read_ir`.
   - Estimate: 1 day

5. Implement hardware adapters with forwarding semantics
   - `DistancePublisher`: publish `distance_IR_short` JSON on configurable MQTT topic; messageID increments deterministically during runs.
   - `ColorSensorAdapter`: expose the color REST endpoints; values driven by `SensorConfig` or simulator responses.
   - `DobotAdapter`: the simulator-side implementation that accepts `/api/dobot/{name}/commands` and updates `SimulationState`.
   - Acceptance: adapters produce the same external shapes/topics as real hardware and can be driven by presets.
   - Estimate: 1.5 days

6. Implement Simulation Engine core
   - `SimulationState` in-memory runtime, deterministic scenario runner executing named presets and updating adapters/state.
   - Engine reads `SensorConfig` to decide outcomes and emits events for the event history.
   - Acceptance: `POST /api/presets/run { "preset": "happy-path" }` progresses steps and triggers expected adapter interactions.
   - Estimate: 1 day

7. REST API, WebSocket, and in-memory event history
   - Control endpoints: `POST /api/presets/run`, `POST /api/presets/stop`, `POST /api/presets/reset`, `GET /api/status`.
   - Sensor config endpoints: `GET /api/config/sensors`, `PUT /api/config/sensors/{id}`.
   - Event history: `GET /api/events` (paged) and WebSocket `/ws/status` streaming state diffs and key events.
   - Acceptance: UI and clients can query status, config sensors, view events, and subscribe to `/ws/status`.
   - Estimate: 1 day

8. SPA Web UI
   - Single-page app to run presets, edit sensor configs, and view event timeline with per-event details.
   - Acceptance: developer can open UI, run `happy-path`, view timeline and change sensor config to reproduce failures.
   - Estimate: 1 day

9. Unit tests
   - Tests for simulation engine determinism, adapter behaviour, and `simulator_client` mapping.
   - Acceptance: `pytest` passes core tests locally.
   - Estimate: 0.75 day

10. Integration test (docker-compose)
   - Compose stack: simulator + minimal consumer (or use `dobot-control` in `--simulation` mode) to run `happy-path` and assert events and state transitions.
   - Acceptance: integration test runs locally and verifies end-to-end happy-path.
   - Estimate: 0.5 day

11. Docker Compose development snippet
   - Add compose snippet wiring `simulated-factory` service and provide env vars (`SIMULATOR_URL`, `SIMULATOR_BROKER_URL`) to `dobot-control` and other consumers.
   - Acceptance: simulator boots in dev compose and `dobot-control` can be run with `--simulation` pointing to it.
   - Estimate: 0.25 day

12. Documentation and README
   - Quick start: running in compose, opening UI, running `happy-path`, toggling failure presets, and how to configure `dobot-control` to use the simulator.
   - Acceptance: developer following README can reproduce happy-path and a failure preset.
   - Estimate: 0.5 day
   
13. Health endpoint and API contract versioning
   - Add a `/health` endpoint and readiness probe that returns `200 OK` when service is ready. Ensure this is mentioned in the `Dockerfile` / compose notes and README for Kubernetes/dev probes where applicable.
   - Ensure `services/simulated-factory/api.md` includes a contract version (e.g. `v1`) and a short changelog or upgrade notes section.
   - Acceptance: `/health` returns `200` when ready; `api.md` declares `v1` and contains example requests/responses.
   - Estimate: 0.25 day

14. Event-bridge configuration docs
   - Document `SIMULATOR_EVENT_BRIDGE` values (`kafka|http|none`) and show example env var configurations for enabling Kafka or HTTP callbacks in the README and `api.md` as appropriate.
   - Acceptance: README includes examples for enabling event bridge modes and required env vars.
   - Estimate: 0.25 day

Total initial prototype estimate: ~5–6 days.

Notes:
- Persistence limited to `presets.yml`; runtime state and event history remain in-memory for MVP.
- Adapter approach recommended: extend `DobotFake` to forward to simulator (minimal changes to existing services).


