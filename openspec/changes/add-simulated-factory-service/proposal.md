# Proposal: Add simulated factory service

What:

- Add a new service, `simulated-factory-service`, which provides a browser-based UI
  and a programmable simulation engine that emulates selected factory hardware and
  the standard order flow used in production.

Scope:

- Hardware covered in the initial MVP:
  - Distance sensor (Tinkerforge): simulated as an MQTT publisher emitting the same
    message format used in production (`distance_IR_short` JSON payloads).
  - Color sensor: simulated REST interface matching the existing color sensor service.
  - Dobot robot arm: simulated REST endpoints matching `services/dobot-control` (move,
    suction, read-color, read-ir, run-flow, etc.).

- Focus: provide the successful order (happy-path) flow. The simulator must allow
  modifying behavior so the flow can fail (e.g., wrong color, missing IR detection),
  but it must not expose manual per-step flow control — failures are injected only
  via sensor/actuator configuration.

Determinism & presets:

- All simulations are deterministic by default. The service exposes a set of named
  presets (e.g. `happy-path`, `wrong-color`, `pickup-failure`) that run reproducibly.

Configuration & UX:

- Configuration available both via REST API and the web UI, with the UI given
  priority for developer workflows. The UI must present a chronological history of
  events (Kafka messages for all topics, REST requests to and from the simualtor, 
  and MQTT messages published by the simulator).

Integration (how it plugs into the existing stack):

- Goal: other services should interact with the simulator using the same interfaces
  they use with real devices (identical REST endpoints, MQTT topics and message
  formats) so no consumer changes are required.

- Integration approach (Adapter pattern — minimal invasive, recommended):
  - Run `dobot-control` with `--simulation` (this uses the existing `DobotFake`).
  - Extend `DobotFake` to accept a `SIMULATOR_URL` (and optional broker config) so it
    can forward actuator commands to the simulator for visualization/recording and
    query sensor values from the simulator for `read_color` / `read_ir` calls.
  - Update `services/dobot-control/config.yml` to include an optional `simulator` section
    with `url`.

Deployment & docker-compose:

- Add `services/simulated-factory` to the development `docker-compose.yml` variant.
- Configure `dobot-control` service in compose to run with `--simulation`.

Persistence & environments:

- The simulator will be a separate service under `services/simulated-factory/`.
- Only a base configuration (named presets and default sensor mappings) is persisted
  on disk as YAML. Runtime state and user edits remain in-memory.

Observability & testing:

- No additional observability requirements (no Prometheus). Implement unit tests for the simulation
  engine and adapters both to verify functionality and detect regressions in future development.

Security & access:

- Local developer-only access; no authentication required.

Why:

- Development environments currently lack the physical hardware required to exercise
  end-to-end flows. This makes testing, demos, and developer productivity harder.
  A local, configurable simulator reduces friction and enables reliable automated tests,
  demos, and onboarding while matching production interfaces.

Goals:

- Web UI to run named presets, view event history, and configure mock hardware values.
- Implement the distance sensor as an MQTT publisher using the production message shape.
- Implement REST-compatible simulation endpoints for the color sensor and Dobot.
- Deterministic named presets to reproduce happy-path and failure scenarios.
- Expose an event history in the UI combining simulator-produced as well as received Kafka messages, incoming and outgoing REST
  requests, and MQTT messages for easy debugging.

Success criteria:

- Developers can run the full order flow locally using `simulated-factory-service` and
  reproduce the named presets deterministically.
- No changes required in consumer services to use the simulator instead of real
  hardware (identical endpoints/topics).

Concrete next steps & tasks:

- Add `simulator` section to `services/dobot-control/config.yml` with `url` and optional broker settings.
- Extend `DobotFake` to call the simulator REST API for sensor reads and POST actuator events.
- Add unit tests for `DobotFake` adapter and simulator client.
- Add `services/simulated-factory` skeleton to `docker-compose` for development and wire `SIMULATOR_URL` env var into `dobot-control`.
- Define a small, versioned API contract file (e.g., `services/simulated-factory/api.md`) describing required endpoints and payload shapes.

Estimated effort:

- 5–6 developer days (includes adapter, simulator skeleton, UI, and tests).
