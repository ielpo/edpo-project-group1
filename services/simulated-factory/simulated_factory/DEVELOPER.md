# Simulated Factory — Developer Guide

This document describes the `simulated_factory` Python backend: its modules,
how they interact, configuration notes, testing pointers and a tasklist to
walk through the codebase.

**Quick Start**
- **App factory**: Use `create_app(config_path)` in [api.py](api.py) to obtain the FastAPI app.
- **Run (example)**:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8400
```

**Architecture (high level)**
- **Entry point**: `create_app()` calls `build_dependencies()` in [deps.py](deps.py) to construct all service components, then installs lifecycle hooks.
- **Engine**: `SimulationEngine` in [engine.py](engine.py) is a monolithic class owning all simulation lifecycle and behaviour:
  - Preset sequencing — run/stop/reset presets, step iteration with delays.
  - Gate awaiting — `awaitRequest` steps block until a matching HTTP request fires the gate (or timeout).
  - Interactive action queue — intercepts dobot commands as a `PendingAction`; resolves on operator approval.
  - Sensor access — delegates to `SensorRegistry` for reads and updates.
  - Actuator commands — delegates to `ActuatorRegistry` for dobot state changes.
- **Sensor registry**: `SensorRegistry` in [sensor_registry.py](sensor_registry.py) loads `config.yml`, instantiates sensor plugins, manages the live sensor pool with MQTT lifecycle (activate/deactivate/pause/resume).
- **Actuator registry**: `ActuatorRegistry` in [actuator_registry.py](actuator_registry.py) owns dobot actuator state, applies command batches, and provides state queries.
- **Runtime snapshot**: `RuntimeSnapshot` in [runtime_snapshot.py](runtime_snapshot.py) composes read-only view models from engine, registries, and adapters for the UI and API.
- **Event store**: `EventStore` in [events.py](events.py) is the central in-memory store for simulator events and used by the SSE endpoint. `EventBridge` (also in `events.py`) is defined for optional HTTP forwarding but is not wired at runtime.
- **Adapters**: `MqttPublisher`, `KafkaObserver`, and `InventoryPoller` live in [adapters/](adapters/) and integrate external systems (MQTT publishing, Kafka consumption, inventory polling).

**Module Summary (concise)**
- **`api.py`**: FastAPI app factory and HTTP/SSE/HTML endpoints. Installs middleware that records requests to the `EventStore` and fires engine gates.
- **`deps.py`**: Dependency factory. Constructs and wires `EventStore`, `MqttPublisher`, `SensorRegistry`, `ActuatorRegistry`, `InventoryPoller`, `SimulationEngine`, and `KafkaObserver`. Returns keys: `event_store`, `mqtt_publisher`, `sensor_registry`, `actuator_registry`, `inventory_poller`, `engine`, `kafka_observer`.
- **`engine.py`**: `SimulationEngine` — monolithic engine class. Owns preset execution, gate management, interactive action interception, and sensor/actuator delegation.
- **`sensor_registry.py`**: `SensorRegistry` — loads `config.yml`, manages the live sensor pool (clone from defaults, wire MQTT publishers, activate/deactivate background tasks), and dynamically instantiates sensor plugins by type inference or explicit `type` field.
- **`actuator_registry.py`**: `ActuatorRegistry` — owns `DobotActuator` instances, applies command batches, provides state queries.
- **`runtime_snapshot.py`**: `RuntimeSnapshot` — composes coherent read-only views (status, presets, twin, events, pending) from multiple registries for UI rendering.
- **`events.py`**: `EventStore` — in-memory event log (bounded deque) with subscriber queues for SSE and `list_events` with pagination and filter modes (`full`/`process`). `EventBridge` — optional HTTP forwarding (defined but not wired).
- **`models.py`**: Pydantic models and dataclasses used across the package: `SimulationState`, `EngineLifecycleState`, `PresetDefinition`/`PresetStep`, `AwaitRequest`, `DobotRuntimeState`, `Position`, `SensorConfig`, `PendingAction`, `InteractiveConfig`, and request/response models.
- **`utils.py`**: Small helpers: `path_pattern_to_regex`, color helpers (`raw_color_from_name`, `rgb_bytes_from_raw`), Kafka payload decoding (`decode_kafka_value`, `decode_kafka_key`), `format_sse`, and `parse_broker_target`.
- **`adapters/mqtt_publisher.py`**: `MqttPublisher` — MQTT publisher that logs publishes to the `EventStore` and performs publish via `paho.mqtt.publish.single`. Wired into `DistanceSensor` instances via `SensorRegistry`.
- **`adapters/kafka_observer.py`**: Passive Kafka consumer that records process-topic messages into the `EventStore` as `KAFKA` events; runs in background and is tolerant of connection failures.
- **`adapters/inventory_poller.py`**: `InventoryPoller` — background `httpx` poll loop fetching inventory from an external URL every 3s.
- **`actuators/base.py`**: Abstract actuator plugin interface; plugins must provide `apply(commands)` and `state()`.
- **`actuators/dobot.py`**: `DobotActuator` — applies the simulator command set (`move`, `move-relative`, `set-speed`, `suction-cup`, `run-conveyor`, `move-conveyor`) to a `DobotRuntimeState`.
- **`sensors/base.py`**: Abstract sensor plugin interface; plugins must provide `read`, `update`, and `to_dict`. `BaseSensor` provides `clone`, `to_config`, `apply_update`. `MqttSensor` extends with `mqtt_message`, `wire`, `publish`, `start_task`/`stop_task`/`pause_task`/`resume_task`.
- **`sensors/color.py`**: `ColorSensor` — supports fixed and scripted modes; returns `(color, raw_color)`. Used for dobot color sensors (sensor IDs prefixed `color-`).
- **`sensors/distance.py`**: Conveyor distance sensor plugin implementing `MqttSensor`; runs a background publishing loop at configured cadence.
- **`sensors/dobot_color.py`**: Legacy dobot color sensor plugin. Superseded by `color.py` for new presets.
- **`sensors/generic.py`**: Fallback sensor with simple value storage used when type inference fails.
- **`sensors/ir.py`**: IR proximity sensor plugin; supports fixed and scripted modes (scripted values indexed by step).

**How the pieces interact (flow)**
1. `create_app(config_path)` calls `build_dependencies(config_path)` which constructs `EventStore`, `MqttPublisher`, `SensorRegistry`, `ActuatorRegistry`, `InventoryPoller`, `SimulationEngine`, and `KafkaObserver`.
2. `api.py` additionally constructs a `RuntimeSnapshot` that references all components for read-only view composition.
3. App startup (lifespan) starts `kafka_observer` and `inventory_poller`. Adapters run in background tasks.
4. Incoming HTTP requests pass through `capture_requests` middleware which:
   - Calls `engine.fire_gate_if_matches(method, path)` to evaluate gated preset steps (applies sensor updates and fires the waiting gate event when matched).
   - Records a `SENSOR_REQUEST` event for `GET /api/dobot/*/color|ir` paths, or a `REST` event otherwise, in `EventStore`.
5. API endpoints call `SimulationEngine` APIs (run/stop/reset presets, read sensors, update sensor config, accept external events and commands).
6. `RuntimeSnapshot` composes coherent views for fragment endpoints and SSE. UI clients subscribe to `/sse/status` to receive server-sent updates rendered as htmx out-of-band swaps.
7. `KafkaObserver` writes external process-topic messages into `EventStore` so they appear alongside simulator-generated events.
8. Distance publishing is handled by `DistanceSensor` (via `MqttSensor` mixin) → `MqttPublisher`; publishes are logged to `EventStore` for observability.

**API Endpoints**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | HTML UI (Jinja2 template) |
| GET | `/health` | Health check |
| GET | `/api/status` | Current `SimulationState` (composed by RuntimeSnapshot) |
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
| GET | `/api/dobot/{name}/state` | Read full dobot state (from ActuatorRegistry) |
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
2. Pauses MQTT sensor publishing via `_sensor_registry.pause()`.
3. Emits a `PENDING_ACTION` event so the UI shows the intercepted command.
4. Waits up to `timeout_seconds` for the operator to call `POST /api/interactive/{action_id}/resolve`.
5. On `outcome=success`: applies commands to `ActuatorRegistry`; on `failure` or timeout: discards them.
6. Resumes MQTT publishing via `_sensor_registry.resume()`.

Only one pending action may exist at a time. If another intercepted command arrives while one is pending, the new command is rejected immediately.

Between preset runs, `intercepted` defaults to all known command types (`_DEFAULT_INTERCEPTED`) so the UI always regains manual control.

**Configuration and environment**
- `config.yml` (path passed to `create_app`) contains `defaults.sensors` and `presets` used by the sensor registry.
- `PresetDefinition` contains `steps` (list of `PresetStep`). Sensor state for a preset is set via `sensorUpdates` in steps.
- Environment variables used in runtime wiring (see `deps.py` and `main.py`):
  - `SIMULATOR_CONFIG_PATH` — path to config YAML (default: `config.yml`)
  - `SIMULATOR_BIND` — HTTP bind address (default: `0.0.0.0`)
  - `SIMULATOR_PORT` — HTTP port (default: `8400`)
  - `SIMULATOR_BROKER_URL` — MQTT broker URL for `MqttPublisher`
  - `INVENTORY_URL` — base URL for inventory polling (default: `http://localhost:8103`)
  - `SIMULATED_FACTORY_KAFKA_OBSERVER` — opt-out flag for starting Kafka observer

**Testing**
- Unit tests live under `services/simulated-factory/tests/`. Run them with:

```bash
cd services/simulated-factory
uv run pytest tests/
```

Key tests: `test_engine.py` (preset execution, gating), `test_events_store.py` (EventStore semantics), `test_sensor_plugins.py` (sensor plugin behavior), `test_pending_action.py` (interactive action lifecycle), `test_api.py` / `test_api_wiring.py` (endpoint contracts), `test_integration.py` (end-to-end flows), `test_components.py` (component isolation), `test_dobot_actuator.py` (actuator command application), `test_sensor_registry.py` (registry lifecycle), `test_actuator_registry.py` (actuator registry).

**Notes & gotchas**
- `SensorRegistry` infers sensor type from ID prefix (`color-` → `color`, `ir-` → `ir`, `distance-` → `distance`); anything else falls back to `generic`. New sensor types must follow the `BaseSensor` contract.
- `sensors/color.py` (`ColorSensor`) is the active color sensor implementation. `sensors/dobot_color.py` (`DobotColorSensor`) is the legacy version.
- `MqttPublisher` handles all MQTT publishing. Distance sensors implement `MqttSensor` and self-publish via a background task when activated by `SensorRegistry.activate()`.
- `EventBridge` is defined in `events.py` but is **not wired** by `build_dependencies()`. It exists for future use.
- The `capture_requests` middleware intentionally fires gates **before** the handler runs so that sensor reads in the handler observe updated state.
- `asyncio.Lock` in `SimulationEngine` guards `run_preset` to prevent concurrent preset starts.
- `RuntimeSnapshot.all_panels()` captures one coherent read cycle so SSE updates are internally consistent across all panels.
- `SensorRegistry.pause()`/`resume()` suspends MQTT background publishing during interactive action resolution to avoid stale publishes while waiting for operator input.

**Tasklist — Walkthrough (check items as you verify code)**
- [ ] Review `api.py` — confirm all endpoints, SSE behaviour, htmx fragment rendering, and middleware gate-firing logic.
- [ ] Inspect `deps.py` — verify environment variable defaults and returned keys.
- [ ] Read `engine.py` — understand preset execution, gate awaiting, and interactive action interception.
- [ ] Read `sensor_registry.py` — verify type inference rules, plugin instantiation, and MQTT lifecycle.
- [ ] Read `actuator_registry.py` — verify command application and state queries.
- [ ] Read `runtime_snapshot.py` — verify view composition and `all_panels()` coherent read.
- [ ] Validate `events.py` — verify `EventStore` subscriber semantics and filter modes.
- [ ] Open `models.py` — confirm Pydantic models align with API contracts.
- [ ] Check `utils.py` — review `path_pattern_to_regex`, color helpers, `parse_broker_target`, and `format_sse`.
- [ ] Walk through `adapters/` — ensure `kafka_observer.py`, `mqtt_publisher.py`, and `inventory_poller.py` are present and healthy.
- [ ] Audit `sensors/` — check all plugins follow `BaseSensor` contract.
- [ ] Audit `actuators/` — check `DobotActuator` command coverage.
- [ ] Run `pytest` and address failing tests.
- [ ] Add or update `config.yml` presets to verify end-to-end flows.
