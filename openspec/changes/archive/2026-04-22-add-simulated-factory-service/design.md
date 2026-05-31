# Design: Simulated Factory Service

## Overview

`simulated-factory-service` provides:
- A REST API and WebSocket endpoint for control and real-time status.
- A small single-page web UI served by the service for local use.
- A simulation engine that runs scenarios (successful, failing, timeout, etc.).
- Hardware adapter implementations that emulate missing devices (color sensor, conveyors, actuators).
- A simple configuration store for preconfigured sensor behaviors.
- An event bridge to optionally publish simulation events to the system event bus (Kafka) or call existing HTTP endpoints.

## Implementation stack (Python)

- Language: Python 3.10+ (based on uv tooling, use `pyproject.toml`)
- Web framework: FastAPI + Uvicorn (async HTTP + WebSocket support)
- Data validation: Pydantic models for all API payloads and `SimulationState`
- MQTT: `paho-mqtt` (sync) or `asyncio-mqtt` (async) for distance sensor publishing
- Kafka: `confluent-kafka-python`
- HTTP client: `httpx` (async) for adapter calls from `DobotFake` / `simulator_client`
- Testing: `pytest` + `pytest-asyncio` for unit and integration tests
- Packaging / deps: `pyproject.toml` using uv for both local and docker
- UI: Svelte + TypeScript served as static assets by the simulator

Rationale: choosing Python aligns with existing Python adapters in the repo and enables rapid prototyping, deterministic scripting, and easy integration with `DobotFake`.

High-level architecture (textual):

  [Web UI] <--> [API / WebSocket] <--> [Simulation Engine] <--> [Hardware Adapters]
                                                     |
                                                     +--> [Event Bridge -> Kafka / HTTP]
                                                     +--> [Config Store (presets.yml — YAML)]

## Components

- Simulation Engine
  - Orchestrates scenarios consisting of ordered steps (receive order, pick, color-check, place).
  - Maintains `SimulationState` (in-memory) and emits events on state change.
  - Supports deterministic delays and failure injection.

- Hardware Adapter Layer
  - Pluggable adapters implementing the same interface as the real hardware drivers.
  - Example adapters: `ColorSensorAdapter`, `ConveyorAdapter`, `ActuatorAdapter`.
  - Adapters return configured values (e.g., color = "red") or simulate errors.

- API & Web UI
  - REST endpoints for start/stop/reset, scenario control, and configuration.
  - WebSocket `/ws/status` for push updates to the UI.
  - A single-file SPA presenting:
    - Simulation controls
    - Timeline / status visualization
    - Sensor config editor

- Event Bridge
  - Module to publish simulation events to Kafka topics used by other services,
    or send HTTP callbacks to existing services. Configurable via env vars.

- Persistence / Config Store
  - Simple YAML file (`presets.yml`) is used to persist named presets and
    default sensor mappings. Runtime edits are kept in-memory.

## Simulator-specific interfaces and constraints

- The simulator must match the interfaces used by the real devices so that other
  services can use the simulator without code changes:
  - Dobot: provide the same REST endpoints as `services/dobot-control` (see that
    project's README). Example endpoints: `/home`, `/move`, `/move-relative`,
    `/set-speed`, `/stop`, `/run-flow`, `/read-color`, `/read-ir`, `/suction-cup`,
    `/run-conveyor`.
  - Color sensor: provide a REST endpoint compatible with the existing color
    sensor service used in the project (e.g. `GET /color` or `/read-color`).
  - Distance sensor (Tinkerforge): publish MQTT messages on the same topics and
    in the same JSON shape the real sensor uses. Make the MQTT topic and broker
    address configurable via env vars.

## Scenarios & Determinism

- The runtime exposes a set of named presets (e.g. `happy-path`, `wrong-color`,
  `pickup-failure`). Each preset is a deterministic script: a defined sequence of
  timed actions and expected sensor outputs. Running a preset executes that script
  end-to-end without requiring manual step control.

- Failure injection is only possible by changing sensor/actuator configuration
  (for example, set `colorSensor.mode=fixed,value=blue` which will cause a color
  mismatch). There is intentionally no API for manual per-step flow control.

## Event History & UI

- Maintain an in-memory chronological event log that records:
  - Kafka events produced by the simulator (if enabled)
  - REST requests received by the simulator (full HTTP metadata + body)
  - MQTT messages published by the simulator (topic + payload)

- The UI presents this event history with filtering (by type/topic/endpoint) and
  per-entry detail view. The UI is the primary way to inspect and tune simulations.

## Adapters

- `DobotAdapter`
  - Implements the Dobot REST contract used by `services/dobot-control`.
  - In simulation mode, replies deterministically and updates `SimulationState`.

- `ColorSensorAdapter`
  - Implements the color sensor REST contract and returns values according to the
    active `SensorConfig` (modes: `fixed`, `random`, `scripted`).

- `DistancePublisher`
  - MQTT publisher that emits messages with the `distance_IR_short` JSON shape
    (sample: `{ "type": "distance_IR_short", "UID": "2a7C", "location": "Conveyor", "messageID": 1273, "distance": 30.0 }`).
  - Topic names and publish cadence are configurable.

## Config store

 Load a base YAML file (`presets.yml`) at startup with named presets and default
 sensor configs. Runtime edits are kept in-memory for the MVP. The YAML is intentionally
 minimal to avoid coupling; it only contains preset definitions and default sensor
 mappings.

## Project layout (suggested)

```
services/simulated-factory/
├── pyproject.toml       # project metadata and deps (or requirements.txt)
├── README.md
├── services/            # optional if multi-process; otherwise single app
├── simulated_factory/   # python package
│   ├── main.py          # FastAPI app entry (uvicorn launch)
│   ├── api.py           # REST + WebSocket endpoints
│   ├── engine.py        # Simulation engine, presets runner
│   ├── adapters/        # DobotAdapter, ColorSensorAdapter, DistancePublisher
│   │   ├── __init__.py
│   │   └── simulator_client.py  # small client used by DobotFake
│   ├── models.py        # Pydantic models (SimulationState, SensorConfig)
│   └── events.py        # event log + websocket broadcaster
├── web/                 # React + TS SPA (Vite)
│   └── README.md
└── presets.yml          # initial named presets (persisted base)
```

## Dependencies (suggested)

- fastapi
- uvicorn[standard]
- pydantic
- httpx[http2]
- paho-mqtt or asyncio-mqtt
- aiokafka or confluent-kafka-python
- pytest, pytest-asyncio
- python-dotenv (for local env overrides)


## APIs (examples)

- GET `/api/status` — returns `SimulationState` (id, status, currentPreset, step).

- POST `/api/simulations/run` — body `{ "preset": "happy-path" }` — starts a
  deterministic run of the named preset.

- POST `/api/simulations/stop` — stops the active run.

- GET `/api/config/sensors` — list sensor configs.

- PUT `/api/config/sensors/{sensorId}` — set sensor behavior `{ "mode": "fixed", "value": "red" }`.

- GET `/api/events` — returns the in-memory event history (paged).

- WebSocket `/ws/status` — streams state diffs and key events.

## Integration details

- Make MQTT topic names, Kafka topics (if event bridge enabled), and REST base
  paths configurable with environment variables so the simulator can be dropped
  into the development compose without editing other services.

### Recommended integration approach (adapter pattern)

- Recommended: run `dobot-control` with its existing `--simulation` flag so the
  service instantiates `DobotFake`.
- Extend `DobotFake` (or add a small `simulator_client` module) so it can forward
  actuator commands to the simulator for UI/recording and query sensor values from
  the simulator for `read_color` / `read_ir` calls. This keeps the integration
  surface minimal and avoids changing other services.
- Behavior requirements for `DobotFake` when connected to a simulator:
  - Non-blocking or low-latency interactions (use short timeouts or background
    updates to avoid blocking HTTP handlers).
  - Clear fallback behaviour if the simulator is unreachable (local deterministic
    defaults, and well-logged warnings).

### Alternative approaches (when to prefer them)

- Event-driven (MQTT/Kafka): `DobotFake` subscribes to simulator sensor topics and
  publishes movement events. Use this when you want to test the full event flow and
  when the simulator should behave as a first-class event producer. This requires
  running a broker in the development stack.
- `pydobotplus` shim: implement a drop-in replacement for `pydobotplus.Dobot` that
  forwards calls to the simulator. Use this when you want to avoid the `--simulation`
  branching in `app.py`, but be aware it's more invasive to maintain API parity.

### Simulator REST contract (minimal, versioned)

- POST `/api/dobot/{name}/commands`
  - Request: list of commands or a single command object (movement, suction, conveyor)
  - Response: 202 Accepted or 200 OK with correlation id
- GET `/api/dobot/{name}/color`
  - Response: `{ "color": "RED", "raw_color": [1,0,0] }`
- GET `/api/dobot/{name}/ir`
  - Response: `{ "ir": true }`
- GET `/api/dobot/{name}/state`
  - Response: current position/speed/conveyor state `{ "position": {..}, "speed": .. }`
- POST `/api/events`
  - Optional: accept simulator events for UI correlation. Body: `{ "type": "movement", "payload": { ... } }`

Include a small `services/simulated-factory/api.md` file in the simulator repo that
documents these endpoints and payload examples. Version the contract (e.g. `v1`) so
changes are explicit.

### Docker / compose notes

- Add `services/simulated-factory` to the developer `docker-compose.yml` and expose
  its REST port and MQTT broker (if used).
- Configure `dobot-control` in compose to run with `--simulation` and provide a
  `SIMULATOR_URL` (and optional `SIMULATOR_BROKER_URL`) environment variable so the
  `DobotFake` adapter can locate the simulator.

- Development snippet: a ready-to-use development compose override is included
  at `openspec/changes/add-simulated-factory-service/docker-compose.dev.yml`.
  Usage example:

  ```bash
  docker compose -f docker-compose.yml -f openspec/changes/add-simulated-factory-service/docker-compose.dev.yml up
  ```

  The snippet wires `simulated-factory`, an MQTT broker (`eclipse-mosquitto`),
  and overrides `dobot-control` to run with `--simulation` and `SIMULATOR_URL`.

### Risks & unknowns

- API contract mismatch: consumers expect certain timing and response shapes — the
  simulator must match these or `dobot-control` adapters must translate.
- Latency and blocking: naive synchronous calls from `DobotFake` to the simulator
  can block HTTP handlers and slow flows. Prefer short timeouts or background
  updates for actuator notifications.
- Unreachable simulator: define clear safe fallback behaviour (deterministic local
  responses, retries, and detailed logging). Decide whether `dobot-control` should
  refuse to start if `--simulation` is requested but simulator is missing.
- Event ordering and determinism: when using brokers, ordering and delivery
  guarantees may differ from synchronous invocation; document expectations.

### Concrete next steps & tasks

- Add `simulator` section to `services/dobot-control/config.yml` with `url` and
  optional `mqtt/kafka` fields.
- Implement `simulator_client.py` (spec/interface only in this change) used by
  `DobotFake` to call the simulator REST endpoints and to subscribe to sensor
  topics if event-driven mode is chosen.
- Add unit tests for `DobotFake` adapter and `simulator_client` that verify:
  - Sensor reads map to simulator responses.
  - Movement commands are forwarded and logged.
- Add `services/simulated-factory/api.md` documenting the minimal REST contract and
  example payloads.
 - Added: `openspec/changes/add-simulated-factory-service/docker-compose.dev.yml`
   — development compose override wiring `simulated-factory`, an MQTT broker,
   and `dobot-control` in `--simulation` mode.
 - Create `pyproject.toml` and a minimal `Dockerfile` for
   `services/simulated-factory`.
 - Add `services/simulated-factory/Dockerfile` and a small `docker-compose` snippet
   for local development (expose REST port and optional MQTT broker).
 - Add `services/simulated-factory/api.md` documenting the minimal REST contract and
   example payloads.
 - Add a small `services/simulated-factory/README.md` with quickstart instructions
   and `docker-compose up` example for developers.

### Sequence diagram (textual)

```
Client (caller) -> dobot-control REST API: POST /run-flow
dobot-control -> DobotFake.execute_dobot_commands: call
DobotFake -> simulator: POST /api/dobot/left/commands (optional async)
DobotFake -> simulator: GET /api/dobot/left/color (for read_color)
simulator -> MQTT/Kafka (optional): publish sensor messages
Other services <- MQTT/Kafka: consume sensor messages
```


## Tests

- Unit tests for the simulation engine and each adapter. Tests verify deterministic
  execution of presets and correct mapping between sensor config and resulting
  behavior.

## APIs (examples)

- GET /api/status
  - Returns current `SimulationState`.

- POST /api/simulations/start
  - Body: `{ "scenario": "happy-path", "speed": "normal" }`
  - Starts a simulation run.

- POST /api/simulations/stop
  - Stops the active simulation.

- POST /api/simulations/reset
  - Resets state to initial.

- GET /api/config/sensors
  - Returns preconfigured sensor settings.

- PUT /api/config/sensors/{sensorId}
  - Sets sensor behavior `{ "mode": "fixed", "value": "red" }`.

- GET /api/scenarios
  - List available scenarios.

- POST /api/scenarios/run
  - Run a scenario programmatically.

WebSocket:
- `/ws/status` — streams JSON messages with state diffs or full state snapshots.

## Data models (sketch)

- SimulationState
  - id, status (idle/running/paused), currentStep, timestamp, items[]

- SensorConfig
  - sensorId, mode (random|fixed|scripted), value, failRate

- ScenarioDefinition
  - id, name, description, steps[], errorInjection[]

## Runtime configuration (env)

- SIMULATOR_BIND=0.0.0.0
- SIMULATOR_PORT=8085
- SIMULATOR_EVENT_BRIDGE=kafka|http|none
- SIMULATOR_CONFIG_PATH=/data/presets.yml

- SIMULATOR_URL=http://simulated-factory:8085   # used by DobotFake
- SIMULATOR_BROKER_URL=tcp://broker:1883         # MQTT broker (optional)
- SIMULATOR_KAFKA_BOOTSTRAP=localhost:9092       # Kafka bootstrap servers (optional)
- SIMULATOR_LOG_LEVEL=INFO
- SIMULATOR_UI_DIR=/app/web/dist                 # path to built UI assets
- PYTHON_ENV=development                         # or production

## Deployment

- Provide `Dockerfile` and `docker-compose` snippet for development.
- Health endpoint `/health` and readiness probe.

## Development mode specifics

- When `SIMULATOR_MODE=development` the service will advertise endpoints that replace missing hardware.
- Other services in compose can be configured to use the simulator's adapters (via environment or config).

## Observability

- MVP: no Prometheus required; rely on structured logs and the in-memory event
  history for debugging and inspection.
- Optionally expose simple, lightweight metrics later if teams want Prometheus
  integration, but it is not part of the initial developer-focused MVP.

## Security & access

- Local developer-only access: the simulator is intended for local development
  and debugging. For the MVP no authentication is required; access should be
  limited to development networks only.

## Success criteria

- Developers can run the full order flow locally using `simulated-factory-service`
  and reproduce the named presets deterministically.
- No code changes are required in consumer services to use the simulator in place
  of real hardware (identical endpoints/topics and message shapes).
- UI provides a chronological event history combining REST requests, MQTT
  messages, and (optionally) Kafka events sufficient to debug end-to-end flows.

## Tradeoffs / Decisions

- Use FastAPI + Uvicorn for quick async WebSocket support and lightweight codebase.
- Keep simulation engine deterministic and easily scriptable, favor clarity over fidelity.

## Tests

- Unit tests for engine and adapters.
- Integration test using docker-compose with a small scenario.
