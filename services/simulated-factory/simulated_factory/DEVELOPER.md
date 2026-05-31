# Simulated Factory — Developer Guide

This document describes the `simulated_factory` Python backend: its modules,
how they interact, configuration notes, testing pointers and a tasklist to
walk through the codebase.

**Quick Start**
- **App factory**: Use `create_app(config_path)` in [api.py](api.py) to obtain the FastAPI app.
- **Run (example)**:

```bash
python -c "from simulated_factory.api import create_app; app = create_app('config.yml'); import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
```

**Architecture (high level)**
- **Entry point**: `create_app()` wires dependencies from [deps.py](deps.py) and installs lifecycle hooks (starts adapters and background pollers).
- **Engine**: `SimulationEngine` in [engine.py](engine.py) is a single class that owns all simulation state and behaviour:
  - Preset sequencing — run/stop/reset presets, step iteration with delays.
  - Gate awaiting — `awaitRequest` steps block until a matching HTTP request fires the gate (or timeout).
  - Sensor management — delegates to `SensorRegistry` for instantiation, holds the active `_sensors` dict.
  - Dobot state — tracks position, speed, suction, and conveyor state per robot; supports command interception.
  - Interactive action queue — intercepts dobot commands as a single active `PendingAction`; resolves it on operator approval.
  - Inventory polling — background task fetching inventory from an external URL every 3 s.
- **Sensor registry**: `SensorRegistry` in [sensor_registry.py](sensor_registry.py) loads `config.yml`, instantiates sensor plugins for defaults, and performs type inference from sensor ID prefixes.
- **Event store**: `EventStore` in [events.py](events.py) is the central in-memory store for simulator events and used by the SSE endpoint in the API. `EventBridge` (also in `events.py`) optionally forwards events to an external HTTP endpoint.
- **Adapters**: Kafka and MQTT adapters live in [adapters/](adapters/) and integrate external process activity (Kafka) and publishing (MQTT).

**Module Summary (concise)**
- **`api.py`**: FastAPI app factory and HTTP/SSE/HTML endpoints. Installs middleware that records requests to the `EventStore` and delegates simulator actions to the `SimulationEngine`.
- **`deps.py`**: Dependency factory. Constructs and wires `EventStore`, `EventBridge`, `MqttPublisher`, `SimulationEngine`, and `KafkaObserver`. Returns keys: `event_store`, `event_bridge`, `mqtt_publisher`, `engine`, `kafka_observer`.
- **`engine.py`**: `SimulationEngine` — monolithic engine class. Owns preset execution, gate management, sensor reads, dobot state, interactive action interception, and inventory polling.
- **`sensor_registry.py`**: `SensorRegistry` — loads `config.yml`, clones default sensors on each preset start, and dynamically instantiates sensor plugins by type inference or explicit `type` field.
- **`events.py`**: `EventStore` — in-memory event log (bounded deque) with subscriber queues for SSE and `list_events` with pagination and filter modes (`full`/`process`). `EventBridge` — optional HTTP forwarding of events to an external target.
- **`models.py`**: Pydantic models and dataclasses used across the package: `SimulationState`, `PresetDefinition`/`PresetStep`, `AwaitRequest`, `DobotRuntimeState`, `Position`, `SensorConfig`, `PendingAction`, `InteractiveConfig`, and request/response models.
- **`utils.py`**: Small helpers: `path_pattern_to_regex`, color helpers (`raw_color_from_name`, `rgb_bytes_from_raw`), Kafka payload decoding (`decode_kafka_value`, `decode_kafka_key`), `format_sse`, and `parse_broker_target`.
- **`adapters/kafka_observer.py`**: Passive Kafka consumer that records process-topic messages into the `EventStore` as `KAFKA` events; runs in background and is tolerant of connection failures.
- **`adapters/mqtt_publisher.py`**: `MqttPublisher` — lightweight MQTT publisher wrapper that logs publishes to the `EventStore` and performs publish via `paho.mqtt.publish.single`. Also used by the engine for `triggerMqtt` step side-effects.
- **`sensors/base.py`**: Abstract sensor plugin interface; plugins must provide `read`, `update`, `apply_update`, `clone`, and `to_config`/`to_dict`. `MqttSensor` extends it with `mqtt_message`.
- **`sensors/color.py`**: `ColorSensor` — supports fixed and scripted modes; returns `(color, raw_color)`. Used for left/right dobot color sensors (sensor IDs prefixed `color-`).
- **`sensors/distance.py`**: Conveyor distance sensor plugin implementing `MqttSensor` for publishing; provides `read`/`update` and MQTT message generation.
- **`sensors/dobot_color.py`**: Legacy dobot color sensor plugin; returns `(color, raw_color)` and accepts `update` to change color. Superseded by `color.py` for new presets.
- **`sensors/generic.py`**: Fallback sensor with simple value storage used when type inference fails.
- **`sensors/ir.py`**: IR proximity sensor plugin; supports fixed and scripted modes (scripted values indexed by step).

**How the pieces interact (flow)**
1. `create_app(config_path)` calls `build_dependencies(config_path)` which constructs `EventStore`, `EventBridge`, `MqttPublisher`, `SimulationEngine`, and `KafkaObserver`.
2. App startup (lifespan) starts `kafka_observer` and the engine's inventory poller. Adapters run in background tasks.
3. Incoming HTTP requests pass through `capture_requests` middleware which:
   - Calls `engine.fire_gate_if_matches(method, path)` to evaluate gated preset steps (applies sensor updates and fires the waiting gate event when matched).
   - Records a `SENSOR_REQUEST` event for `GET /api/dobot/*/color|ir` paths, or a `REST` event otherwise, in `EventStore`.
4. API endpoints call `SimulationEngine` APIs (run/stop/reset presets, read sensors, update sensor config, accept external events and commands).
5. `SimulationEngine` records state changes and actions to `EventStore`. UI clients subscribe to `/sse/status` to receive server-sent updates rendered as htmx out-of-band swaps.
6. `KafkaObserver` writes external process-topic messages into `EventStore` so they appear alongside simulator-generated events.
7. Distance publishes and MQTT activity are submitted via `MqttPublisher`; publishes are also logged to `EventStore` for observability.

**API Endpoints**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | HTML UI (Jinja2 template) |
| GET | `/health` | Health check |
| GET | `/api/status` | Current `SimulationState` |
| GET | `/api/presets` | List all presets |
| POST | `/api/presets/run` (or `/api/simulations/run`) | Start a preset |
| POST | `/api/presets/stop` (or `/api/simulations/stop`) | Request stop |
| POST | `/api/presets/reset` (or `/api/simulations/reset`) | Hard reset |
| GET | `/api/config/sensors` | List sensor configs |
| PUT | `/api/config/sensors/{sensor_id}` | Update a sensor (always returns JSON) |
| GET | `/api/inventory` | Return inventory cache |
| GET | `/api/events` | Paginated event log (supports `page`, `pageSize`, `filter`, `mode`) |
| POST | `/api/events` | Accept an external event |
| POST | `/api/dobot/{name}/commands` | Submit dobot commands (intercepted if interactive) |
| GET | `/api/dobot/{name}/color` | Read dobot color sensor |
| GET | `/api/dobot/{name}/ir` | Read dobot IR sensor |
| GET | `/api/dobot/{name}/state` | Read full dobot state |
| GET | `/api/interactive/config` | Get interactive intercept config |
| PUT | `/api/interactive/config` | Update interactive intercept config |
| GET | `/api/interactive/pending` | List pending (intercepted) actions |
| POST | `/api/interactive/{action_id}/resolve` | Resolve a pending action |
| GET | `/color`, `/api/color` | RGB bytes for left color sensor |
| GET | `/read-color` | Color + raw_color for left sensor |
| GET | `/read-ir` | IR value for left sensor |
| GET | `/sse/status` | SSE stream — sends htmx OOB fragment updates on every event |
| GET | `/fragments/status` | htmx status panel |
| GET | `/fragments/presets` | htmx presets panel |
| GET | `/fragments/twin` | htmx digital twin panel |
| GET | `/fragments/events` | htmx event log panel |
| GET | `/fragments/pending` | htmx pending actions panel |

**Interactive Action System**

When `InteractiveConfig.intercepted` contains command types (e.g. `move`, `suction-cup`), `handle_dobot_commands` intercepts matching commands:
1. Creates a `PendingAction` and stores it in `engine._pending_action`.
2. Emits a `PENDING_ACTION` event so the UI shows the intercepted command.
3. Waits up to `timeout_seconds` for the operator to call `POST /api/interactive/{action_id}/resolve`.
4. On `outcome=success`: applies commands to `DobotRuntimeState`; on `failure` or timeout: discards them.

Only one pending action may exist at a time. If another intercepted command arrives while one is pending, the new command is rejected immediately instead of being queued.

Between preset runs, `intercepted` defaults to all known command types (`_DEFAULT_INTERCEPTED`) so the UI always regains manual control.

**Configuration and environment**
- `config.yml` (path passed to `create_app`) contains `defaults.sensors` and `presets` used by the engine.
- `PresetDefinition` contains `steps` (list of `PresetStep`). Initial sensor state for a preset is set via `sensorUpdates` in the first step.
- Environment variables used in runtime wiring (see `deps.py`):
  - `SIMULATOR_EVENT_BRIDGE`, `SIMULATOR_EVENT_BRIDGE_URL` — event bridge mode/target
  - `SIMULATOR_BROKER_URL` — MQTT broker URL for `MqttPublisher`
  - `SIMULATED_FACTORY_KAFKA_OBSERVER` — opt-out flag for starting Kafka observer
  - `INVENTORY_URL` — base URL for inventory polling (default: `http://localhost:8103`)

**Testing**
- Unit tests live under `services/simulated-factory/tests/`. Run them with:

```bash
cd services/simulated-factory
pytest -q
```

Key tests: `test_engine.py` (preset execution, gating), `test_events_store.py` (EventStore semantics), `test_sensor_plugins.py` (sensor plugin behavior), `test_pending_action.py` (interactive action lifecycle), `test_api.py` / `test_api_wiring.py` (endpoint contracts), `test_integration.py` (end-to-end flows), `test_components.py` (component isolation).

**Notes & gotchas**
- `SensorRegistry` infers sensor type from ID prefix (`color-` → `color`, `ir-` → `ir`, `distance-` → `distance`); anything else falls back to `generic`. New sensor types must follow the `BaseSensor` contract and provide a `<Type>SensorConfig` Pydantic model in the same module.
- `sensors/color.py` (`ColorSensor`) is the active color sensor implementation. `sensors/dobot_color.py` (`DobotColorSensor`) is the legacy version and should only be used when an existing config explicitly sets `type: dobot_color`.
- `MqttPublisher` handles all MQTT publishing. There is no separate `DistancePublisher`; distance sensors implement `MqttSensor` and are triggered by `triggerMqtt: true` steps in the engine.
- `EventBridge` is defined in `events.py` alongside `EventStore`. It is constructed in `deps.py` and passed to the engine, but the engine currently does not call it directly — `EventBridge.emit` is available for future use.
- The `capture_requests` middleware intentionally fires gates **before** the handler runs so that sensor reads in the handler observe updated state.
- `asyncio.Lock` in `SimulationEngine` guards `run_preset` to prevent concurrent preset starts; a running task must finish or be stopped/reset before a new one can start.

**Tasklist — Walkthrough (check items as you verify code)**
- [ ] Review `api.py` — confirm all endpoints, SSE behaviour, htmx fragment rendering, and middleware gate-firing logic.
- [ ] Inspect `deps.py` — verify environment variable defaults and returned keys.
- [ ] Read `engine.py` — understand preset execution, gate awaiting, interactive action interception, and inventory polling.
- [ ] Read `sensor_registry.py` — verify type inference rules and plugin instantiation via `importlib`.
- [ ] Validate `events.py` — verify `EventStore` subscriber semantics, filter modes, and `EventBridge` wiring.
- [ ] Open `models.py` — confirm Pydantic models align with API contracts, especially `InteractiveConfig` and `PendingAction`.
- [ ] Check `utils.py` — review `path_pattern_to_regex`, color helpers, `parse_broker_target`, and `format_sse`.
- [ ] Walk through `adapters/` — ensure `kafka_observer.py` and `mqtt_publisher.py` are present and healthy.
- [ ] Audit `sensors/` — add unit tests for any new plugin; prefer `color.py` over `dobot_color.py` for new color sensors.
- [ ] Run `pytest` and address failing tests; focus on engine/preset behavior, EventStore replay, and interactive action lifecycle.
- [ ] Add or update `config.yml` presets to verify end-to-end flows (sensor updates, `triggerMqtt` publishes, and gates).
