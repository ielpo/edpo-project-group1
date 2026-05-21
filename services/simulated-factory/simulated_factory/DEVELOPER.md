# Simulated Factory — Developer Guide

This document describes the `simulated_factory` Python backend: its modules,
how they interact, configuration notes, testing pointers and a tasklist to
walk through the codebase.

**Quick Start**
- **App factory**: Use `create_app(config_path)` in [services/simulated-factory/simulated_factory/api.py](services/simulated-factory/simulated_factory/api.py) to obtain the FastAPI app.
- **Run (example)**: create a tiny runner `run.py` with `app = create_app("config.yml")` and start with:

```bash
python -c "from simulated_factory.api import create_app; app = create_app('config.yml'); import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
```

**Architecture (high level)**
- **Entry point**: `create_app()` wires dependencies from [deps.py](services/simulated-factory/simulated_factory/deps.py) and installs lifecycle hooks (starts adapters and background pollers).
- **Engine (facade)**: `SimulationEngine` in [engine/\_\_init\_\_.py](services/simulated-factory/simulated_factory/engine/__init__.py) is a thin facade that delegates to three internal components:
  - **ProcessRunner** (`engine/process_runner.py`) — owns preset step sequencing, gate awaiting, distance publishing, and side-effect execution.
  - **ControlPointManager** (`engine/control_points.py`) — owns request gates, pending actions, and dobot command interception/resolution.
  - **ResourceManager** (`engine/resources.py`) — owns sensor plugins, dobot state, config loading, and inventory polling.
- **Runtime model**: `engine/runtime.py` defines internal mutable dataclasses (`FactoryState`, `ProcessState`, `ControlState`, `PhysicalResources`, `SimulationRuntime`) that hold all engine state. The public API returns immutable Pydantic snapshots from `models.py`.
- **Event store**: `EventStore` in [events.py](services/simulated-factory/simulated_factory/events.py) is the central in-memory store for simulator events and used by the SSE endpoint in the API.
- **Adapters**: Kafka and MQTT adapters live in [adapters/](services/simulated-factory/simulated_factory/adapters) and integrate external process activity (Kafka) and publishing (MQTT). `DistancePublisher` (`adapters/distance_publisher.py`) handles MQTT distance sensor publishes.
- **Sensors**: Sensor plugins under [sensors/](services/simulated-factory/simulated_factory/sensors) implement a small plugin API used by the engine to read/update sensor state.

**Module Summary (concise)**
- **`services/simulated-factory/simulated_factory/api.py`**: FastAPI app factory and HTTP/SSE/HTML endpoints. Installs middleware that records requests to the `EventStore` and delegates simulator actions to the `SimulationEngine`.
- **`services/simulated-factory/simulated_factory/deps.py`**: Dependency factory. Constructs and wires `EventStore`, (optional) `EventBridge`, distance/ MQTT publishers, `SimulationEngine`, and `KafkaObserver` for consistent runtime wiring.
- **`services/simulated-factory/simulated_factory/engine/__init__.py`**: `SimulationEngine` facade. Constructs and wires internal components, exposes the full public API unchanged, and provides backward-compatible properties (`_step_gate`, `_run_task`, `_inventory_cache`) for existing tests.
- **`services/simulated-factory/simulated_factory/engine/runtime.py`**: Internal mutable runtime model (dataclasses). `SimulationRuntime` aggregates `FactoryState`, `ProcessState`, `ControlState`, and `PhysicalResources`. Provides `reset()` for clean restarts.
- **`services/simulated-factory/simulated_factory/engine/process_runner.py`**: Preset step sequencing. Responsibilities: run/stop presets, execute steps sequentially, await step gates with timeout, apply step side-effects (sensor updates, distance publishes).
- **`services/simulated-factory/simulated_factory/engine/control_points.py`**: Request gate management. Responsibilities: evaluate `fire_gate_if_matches()` against pending gates, manage `PendingAction` lifecycle, intercept and apply dobot commands.
- **`services/simulated-factory/simulated_factory/engine/resources.py`**: Physical resource management. Responsibilities: load config, instantiate sensor plugins, expose `read_color`/`read_ir`/`update_sensor`, manage dobot state dict, run background inventory polling.
- **`services/simulated-factory/simulated_factory/events.py`**: `EventStore` — in-memory event log with subscriber queues for SSE and utilities to list and filter events.
- **`services/simulated-factory/simulated_factory/models.py`**: Pydantic models and small dataclasses used across the package: `SimulationState`, `PresetDefinition`/`PresetStep`, `SensorConfig`, request/response models and `PendingAction`.
- **`services/simulated-factory/simulated_factory/utils.py`**: Small helpers used across modules: path-pattern → regex, color helpers, Kafka payload decoding and SSE formatting.
- **`services/simulated-factory/simulated_factory/adapters/kafka_observer.py`**: Passive Kafka consumer that records process-topic messages into the `EventStore` as `KAFKA` events; runs in background and is tolerant of connection failures.
- **`services/simulated-factory/simulated_factory/adapters/mqtt_publisher.py`**: Lightweight MQTT publisher wrapper that logs publishes to the `EventStore` and performs a simple publish via `paho.mqtt.publish.single`.
- **`services/simulated-factory/simulated_factory/sensors/base.py`**: Abstract sensor plugin interface; plugins must provide `read`, `update`, and `to_dict` (and optionally MQTT topic/payload methods).
- **`services/simulated-factory/simulated_factory/sensors/distance.py`**: Conveyor distance sensor plugin implementing `MqttSensor` for publishing; provides `read`/`update` and MQTT message generation.
- **`services/simulated-factory/simulated_factory/sensors/dobot_color.py`**: Dobot color sensor plugin; returns `(color, raw_color)` and accepts `update` to change color.
- **`services/simulated-factory/simulated_factory/sensors/generic.py`**: Fallback sensor with simple value storage used when type inference fails.
- **`services/simulated-factory/simulated_factory/sensors/ir.py`**: IR proximity sensor plugin; supports fixed and scripted modes (scripted values indexed by step).
- **`services/simulated-factory/simulated_factory/sensors/sensor_loader.py`**: Dynamic loader helper that imports sensor modules and builds typed config objects.

**How the pieces interact (flow)**
1. `create_app(config_path)` calls `build_dependencies(config_path)` which constructs `EventStore`, publisher adapters, `SimulationEngine`, and `KafkaObserver`.
2. App startup (lifespan) starts `kafka_observer` and the engine's inventory poller. Adapters run in background tasks.
3. Incoming HTTP requests pass through `capture_requests` middleware which:
   - Calls `engine.fire_gate_if_matches(method, path)` to evaluate gated preset steps (this makes request-driven gates visible to presets).
   - Records an event in `EventStore` for UI visibility.
4. API endpoints call `SimulationEngine` APIs (run/stop/reset presets, read sensors, update sensor config, accept external events and commands).
5. `SimulationEngine` records state changes and actions to `EventStore`. UI clients subscribe to `/sse/status` to receive server-sent updates.
6. `KafkaObserver` writes external process-topic messages into `EventStore` so they appear alongside simulator-generated events.
7. Distance publishes and MQTT activity are submitted via publisher adapters; publishes are also logged to `EventStore` for observability.

**Configuration and environment**
- `config.yml` (path passed to `create_app`) contains `defaults.sensors` and `presets` used by the engine.
- Environment variables used in runtime wiring (see `deps.py`):
  - `SIMULATOR_EVENT_BRIDGE`, `SIMULATOR_EVENT_BRIDGE_URL` — event bridge mode/target
  - `SIMULATOR_BROKER_URL` — used by distance/MQTT publisher factories
  - `SIMULATED_FACTORY_KAFKA_OBSERVER` — opt-out flag for starting Kafka observer

**Testing**
- Unit tests live under `services/simulated-factory/tests/`. Run them with:

```bash
cd services/simulated-factory
pytest -q
```

Key tests exercise `EventStore`, engine behavior, sensor logic and utilities.

**Notes & gotchas**
- The engine uses dynamic plugin loading for sensors. New sensor types must follow the `BaseSensor` contract and (optionally) provide a `<Type>SensorConfig` Pydantic model.
- Adapters should be resilient: the Kafka observer is intentionally passive and non-fatal on connection errors; MQTT publishes are best-effort and logged to `EventStore`.
- During review you may notice references to `DistancePublisher` and `EventBridge` in the wiring code and tests — ensure corresponding adapter implementations or wrappers exist in `adapters/`.

**Tasklist — Walkthrough (check items as you verify code)**
- [ ] Review `services/simulated-factory/simulated_factory/api.py` — confirm endpoints and SSE behavior.
- [ ] Inspect `services/simulated-factory/simulated_factory/deps.py` — verify environment variable defaults and returned keys.
- [ ] Read `services/simulated-factory/simulated_factory/engine.py` — understand preset execution, gating and sensor lifecycle.
- [ ] Validate `services/simulated-factory/simulated_factory/events.py` — verify `EventStore` subscriber semantics and filtering.
- [ ] Open `services/simulated-factory/simulated_factory/models.py` — confirm Pydantic models align with API contracts.
- [ ] Check `services/simulated-factory/simulated_factory/utils.py` — review helpers used by engine/adapters.
- [ ] Walk through `services/simulated-factory/simulated_factory/adapters/*` — ensure `kafka_observer.py`, `mqtt_publisher.py` and any `distance_publisher.py` are present and healthy.
- [ ] Audit `services/simulated-factory/simulated_factory/sensors/*` — add unit tests for any new plugin you introduce.
- [ ] Run `pytest` and address failing tests; focus on engine/preset behavior and EventStore replay.
- [ ] Add or update `config.yml` presets to verify end-to-end flows (sensor updates, publishDistance and gates).

If you want, I can:
- update this file with additional diagrams, sequence examples, or inline code pointers; or
- generate a minimal `run.py` and a `config.example.yml` to make the service runnable locally.

---
Generated from a code inspection of the package modules; keep this file next to the code for quick onboarding.
