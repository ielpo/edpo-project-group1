# Simulated Factory — Architecture

The **Simulated Factory** is a FastAPI service that emulates a physical factory
(Dobot arms, conveyors, sensors). It executes scripted presets (step sequences),
exposes a REST/SSE API for dashboards and orchestrators, and integrates with
Kafka and MQTT for event-driven communication.

This document is text-only by design — every diagram is also available as a
renderable [D2](https://d2lang.com) source file under [`diagrams/`](./diagrams).
Render with `d2 diagrams/<file>.d2 <file>.svg`, or paste the file contents
into <https://play.d2lang.com>.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Inventory](#component-inventory)
3. [Engine — Core Domain](#engine--core-domain)
4. [Registries](#registries)
5. [Sensor Plugin System](#sensor-plugin-system)
6. [Actuator Plugin System](#actuator-plugin-system)
7. [API / Domain Models](#api--domain-models)
8. [Adapters & Events](#adapters--events)
9. [Dependency Wiring](#dependency-wiring)
10. [Lifecycle](#lifecycle)
11. [Preset Execution Flow](#preset-execution-flow)
12. [Key Design Decisions](#key-design-decisions)
13. [Diagram Index](#diagram-index)

---

## System Overview

```
                                EXTERNAL
                                --------

      Dashboard          Orchestrator       Inventory       Kafka        MQTT
       (HTMX)            (Dobot Ctrl)        Service       Broker      Broker
          |                   |                  ^            ^           ^
          | HTTP/SSE          | REST             | poll       | consume   | publish
          v                   v                  |            |           |
   +======+===================+==================+============+===========+======+
   |                                                                             |
   |                       SIMULATED FACTORY SERVICE                             |
   |                                                                             |
   |   +------------------- API Layer (FastAPI) -------------------+             |
   |   |  REST endpoints  |  SSE stream  |  HTMX fragments         |             |
   |   |               Request-Capture Middleware                  |             |
   |   +-------------------------+--------------------------------+              |
   |                             | fire_gate_if_matches() + dispatch             |
   |                             v                                               |
   |   +------------ SimulationEngine (monolithic) -------------+                |
   |   |  preset execution | gate matching | interactive mode   |                |
   |   |  sensor reads     | command dispatch                   |                |
   |   +-----+----------------------------+--------------------+                 |
   |         |                             |                                     |
   |         v                             v                                     |
   |   SensorRegistry                ActuatorRegistry                            |
   |   (live sensor pool +            (dobot state +                             |
   |    plugin lifecycle)              command application)                       |
   |                                                                             |
   |   Sensor plugins (color, ir, distance, generic, dobot_color)                |
   |   Actuator plugins (DobotActuator)                                          |
   |                                                                             |
   |   RuntimeSnapshot (composes read-only views for UI/API)                     |
   |                                                                             |
   |   +---- Adapters ----+        +----- Events -----+                          |
   |   |  KafkaObserver   |        |   EventStore     | <-- SSE subscribers      |
   |   |  MqttPublisher   |        |   EventBridge    | (defined, not wired)     |
   |   |  InventoryPoller |        +------------------+                          |
   |   +--+--------+---+--+                                                     |
   +------|--------|---|-----------------------------------------------------+   |
          |        |   |                                                         |
          |        |   +-------------- poll /inventory ----------> (Inventory)   |
          |        +-------------- MQTT publish ---------------> (MQTT)          |
          +------------- consumes Kafka topics ----------------> (Kafka)         |
```

> **D2 source:** [`diagrams/01-component.d2`](./diagrams/01-component.d2)

---

## Component Inventory

| Layer      | Component            | File                            | Responsibility                                                       |
|------------|----------------------|---------------------------------|----------------------------------------------------------------------|
| API        | FastAPI app + middleware | `api.py`                     | HTTP/SSE surface, request capture, HTMX fragments                    |
| API        | RuntimeSnapshot      | `runtime_snapshot.py`           | Composes read-only view models from multiple registries              |
| API        | Dependency wiring    | `deps.py`                       | Builds and wires all service dependencies                           |
| Engine     | SimulationEngine     | `engine.py`                     | Monolithic engine: preset execution, gate matching, interactive mode |
| Registries | SensorRegistry       | `sensor_registry.py`            | Plugin instantiation, live sensor pool, MQTT lifecycle               |
| Registries | ActuatorRegistry     | `actuator_registry.py`          | Dobot actuator state, command application, reset                    |
| Sensors    | BaseSensor + plugins | `sensors/`                      | Pluggable sensor implementations                                     |
| Actuators  | BaseActuator + plugins | `actuators/`                  | Pluggable actuator implementations (currently DobotActuator)        |
| Adapters   | MqttPublisher        | `adapters/mqtt_publisher.py`    | MQTT publish + EventStore logging                                    |
| Adapters   | KafkaObserver        | `adapters/kafka_observer.py`    | Read-only Kafka consumer feeding the event store                     |
| Adapters   | InventoryPoller      | `adapters/inventory_poller.py`  | Background polling of external inventory service                     |
| Events     | EventStore           | `events.py`                     | In-memory event log + pub/sub queues for SSE                         |
| Events     | EventBridge          | `events.py`                     | Optional HTTP relay (defined but not wired at runtime)               |
| Models     | Pydantic + dataclasses | `models.py`                   | API + domain shapes                                                  |
| Utils      | Utility functions    | `utils.py`                      | Path-pattern regex, color helpers, broker parsing                    |

---

## Engine — Core Domain

The engine is a single monolithic class (`SimulationEngine`) that owns all
simulation lifecycle state and delegates data ownership to two registries:
`SensorRegistry` (sensor plugins) and `ActuatorRegistry` (dobot state).

### Engine responsibilities

| Concern                | What the engine does                                                              |
|------------------------|-----------------------------------------------------------------------------------|
| Preset lifecycle       | `run_preset()`, `stop()`, `reset()` — manages run_id, status, asyncio task       |
| Step execution         | `_execute_preset()`, `_run_step()` — iterates steps, applies delays              |
| Gate matching          | `fire_gate_if_matches()`, `_await_gate()` — blocks on `asyncio.Event`            |
| Interactive mode       | `handle_dobot_commands()`, `resolve_action()` — intercepts commands               |
| Sensor access          | `read_color()`, `read_ir()`, `update_sensor()` — delegates to `SensorRegistry`   |
| Event recording        | `_record_event()` — appends to `EventStore`                                       |

### Engine state (direct attributes)

```
SimulationEngine
|
+-- Lifecycle:         _status, _run_id, _run_counter, _current_preset,
|                      _current_step, _current_step_name, _stop_requested,
|                      _run_task, _lock
|
+-- Gate/Interactive:  _step_gate, _waiting_for_request,
|                      _pending_action, _interactive_config
|
+-- Registries:        _sensor_registry (SensorRegistry),
|                      _actuator_registry (ActuatorRegistry)
|
+-- Infrastructure:    event_store (EventStore),
                       _mqtt_publisher (MqttPublisher)
```

> **D2 source:** [`diagrams/02-runtime-state.d2`](./diagrams/02-runtime-state.d2)

### `SimulationEngine` API

| Method                                                   | Returns                  | Purpose                                                       |
|----------------------------------------------------------|--------------------------|---------------------------------------------------------------|
| `get_status()`                                           | `EngineLifecycleState`   | Lifecycle snapshot (no dobot/sensor state)                    |
| `run_preset(name, speed)`                                | `str` (run_id)           | Start a preset run                                            |
| `stop()`                                                 | —                        | Request stop on the current run                               |
| `reset()`                                                | —                        | Cancel current run, reset all state                           |
| `fire_gate_if_matches(method, path)`                     | `bool`                   | Trigger the preset step gate if it matches                    |
| `handle_actuator_commands(robot, payload)`               | `dict`                   | Execute or intercept actuator commands                        |
| `resolve_action(id, outcome, reason)`                    | `PendingAction`          | Resolve a pending intercepted action                          |
| `get_pending_actions()`                                  | `list`                   | Currently waiting actions                                     |
| `get_interactive_config()` / `set_interactive_config()`  | `InteractiveConfig`      | Interactive interception config                               |
| `update_sensor(id, update)`                              | `SensorConfig`           | Apply mode/value update to a sensor                           |
| `read_color(robot)`                                      | `tuple[str, list[int]]`  | Color sensor read                                             |
| `read_ir(robot)`                                         | `bool`                   | IR sensor read                                                |
| `read_color_sensor_bytes()`                              | `dict`                   | RGB-byte view of the left color sensor                        |
| `record_external_event(payload)`                         | —                        | Inject an external event into `EventStore`                    |

> **D2 source:** [`diagrams/03-engine-class.d2`](./diagrams/03-engine-class.d2)

---

## Registries

### SensorRegistry

Lives in `sensor_registry.py`. Sole owner of the sensor plugin pool.

| Method / Property                    | Purpose                                                          |
|--------------------------------------|------------------------------------------------------------------|
| `get_presets()`                      | Parsed `PresetDefinition`s from config YAML                      |
| `sensors()`                          | Clone of default sensors (for reference)                         |
| `reset()`                            | Rebuild live pool from defaults                                  |
| `get_or_create(sensor_id)`           | Return live sensor or create+wire a new one                      |
| `activate()` / `deactivate()`        | Start/stop MQTT background tasks for all MqttSensors            |
| `pause()` / `resume()`              | Suspend/resume MQTT publishing (used during interactive mode)    |
| `apply_updates(updates)`             | Apply sensor value changes from a preset step                    |
| `configs()`                          | Return configs for all live sensors                              |
| `apply_sensor_update(id, update)`    | Apply an API update and return updated config                    |
| `make(sensor_id, config)`            | Public plugin instantiation via importlib                        |
| `live`                               | Read-only access to the live sensor dict                         |

### ActuatorRegistry

Lives in `actuator_registry.py`. Sole owner of dobot actuator state.

| Method                              | Purpose                                                          |
|-------------------------------------|------------------------------------------------------------------|
| `apply_commands(robot_name, cmds)`  | Apply a command batch to the named actuator                      |
| `get_state(robot_name)`             | Deep copy of one actuator's current state                        |
| `all_states()`                      | Deep copies of all actuators keyed by name                       |
| `reset()`                           | Rebuild all actuators to default state                           |

---

## Sensor Plugin System

### Plugin discovery

`SensorRegistry.make(sensor_id, config)` performs dynamic loading:

1. Infer the plugin type from `config["type"]`, or fall back to a sensor-id
   prefix rule (`color-*` → `color`, `ir-*` → `ir`, `distance-*` → `distance`,
   anything else → `generic`).
2. Import `simulated_factory.sensors.<type>` and look up `<Type>Sensor` and
   optionally `<Type>SensorConfig`.
3. Build a config instance (typed if a `*Config` class exists, otherwise a
   plain `SensorConfig`).
4. Instantiate `<Type>Sensor(sensor_id, cfg)`.

Sensors are cloned from defaults on each `reset()` so step-level updates do
not mutate the default plugins.

### Built-in plugins

| Type          | Class               | Read returns             | Config highlights                                                          |
|---------------|---------------------|--------------------------|----------------------------------------------------------------------------|
| `color`       | `ColorSensor`       | `tuple[str, list[int]]`  | `mode`, `value`, `raw_color`, `scripted_values`                            |
| `ir`          | `IrSensor`          | `bool`                   | `mode`, `value`, `scripted_values`                                         |
| `distance`    | `DistanceSensor`*   | `float`                  | `mode`, `value`, `mqtt_topic`, `uid`, `location`, `cadence_ms`             |
| `generic`     | `GenericSensor`     | `Any`                    | Fallback for unrecognized types                                            |
| `dobot_color` | `DobotColorSensor`  | `tuple[str, list[int]]`  | Legacy color sensor (prefer `color` for new presets)                       |

*`DistanceSensor` also implements `MqttSensor` and runs a background
publishing task when activated.

### Plugin interface

```
BaseSensor (ABC)
   +name: str
   -_cfg: SensorConfig
   +read(step)             (abstract)
   +update(value)          (abstract)
   +to_dict()              (abstract)
   +clone()                deep copy via to_config()
   +to_config()            return deep copy of _cfg
   +apply_update(data)     apply dict of updates to _cfg

MqttSensor (ABC mix-in)
   +mqtt_message()         (abstract) -> (topic, payload) | None
   +wire(publisher)        attach MqttPublisher
   +publish()              call publisher.publish_raw(topic, payload)
   +start_task()           start background publishing loop
   +stop_task()            cancel background task
   +pause_task()           suspend publishing
   +resume_task()          resume publishing
```

> **D2 source:** [`diagrams/04-sensor-class.d2`](./diagrams/04-sensor-class.d2)

---

## Actuator Plugin System

### Plugin interface

```
BaseActuator (ABC)
   +name: str
   +apply(commands)        (abstract) mutate state from command batch
   +state()                (abstract) return deep copy of current state
```

### Built-in plugins

| Class            | State model          | Supported commands                                                |
|------------------|----------------------|-------------------------------------------------------------------|
| `DobotActuator`  | `DobotRuntimeState`  | `move`, `move-relative`, `set-speed`, `suction-cup`, `run-conveyor`, `move-conveyor` |

---

## API / Domain Models

### Live state

| Model                | Kind     | Purpose                                                                |
|----------------------|----------|------------------------------------------------------------------------|
| `SimulationStatus`   | enum     | `IDLE` / `RUNNING` / `STOPPED`                                         |
| `EngineLifecycleState` | pydantic | Lifecycle-only snapshot returned by `engine.get_status()`            |
| `SimulationState`    | pydantic | Full `/api/status` payload (lifecycle + dobots), composed by `RuntimeSnapshot` |
| `DobotRuntimeState`  | pydantic | Per-dobot pose, suction, conveyor state                                |
| `Position`           | pydantic | `x, y, z, r`                                                           |
| `AwaitRequest`       | pydantic | `method, path` pair used by gates                                      |

### Preset definitions

| Model               | Kind     | Purpose                                                                |
|---------------------|----------|------------------------------------------------------------------------|
| `PresetDefinition`  | pydantic | `name, description, steps[]`                                           |
| `PresetStep`        | pydantic | `name, delayMs, note?, triggerMqtt?, sensorUpdates, awaitRequest?`     |

### Control / events

| Model               | Kind      | Purpose                                                                |
|---------------------|-----------|------------------------------------------------------------------------|
| `PendingAction`     | dataclass | Action awaiting decision; has `resolve()` / `wait_for_resolution()`    |
| `InteractiveConfig` | pydantic  | `intercepted: set[str]`, `timeout_seconds: int`                        |
| `EventEntry`        | pydantic  | Event log row stored by `EventStore`                                   |

### Request DTOs

| Model                       | Used by                                  |
|-----------------------------|------------------------------------------|
| `RunPresetRequest`          | `POST /api/presets/run`                  |
| `SensorUpdateRequest`       | `PUT /api/config/sensors/{id}`           |
| `InteractiveConfigRequest`  | `PUT /api/interactive/config`            |
| `ResolveActionRequest`      | `POST /api/interactive/{id}/resolve`     |

> **D2 source:** [`diagrams/05-models-class.d2`](./diagrams/05-models-class.d2)

---

## Adapters & Events

### Adapter status

| Adapter             | Wired by `deps.py`? | Direction              | Notes                                                                                       |
|---------------------|---------------------|------------------------|---------------------------------------------------------------------------------------------|
| `MqttPublisher`     | yes                 | service → MQTT         | Always logs an `MQTT` event; only publishes if `SIMULATOR_BROKER_URL` is set and `paho.mqtt` is importable |
| `KafkaObserver`     | yes                 | Kafka → service        | Read-only; appends `KAFKA` events. Failures are non-fatal                                  |
| `InventoryPoller`   | yes                 | Inventory → service    | Background `httpx` poll loop every 3s; caches the inventory grid                           |
| `EventBridge`       | **no**              | (defined, not wired)   | Class exists in `events.py` but is not instantiated by `build_dependencies()`              |

### EventStore

In-memory bounded `deque` (default `max_entries=500`) plus a set of subscriber
`asyncio.Queue`s. Each appended event is delivered to subscribers via
`put_nowait`, dropping when a queue is full (subscriber queue size is
`EVENT_SUBSCRIBER_QUEUE_SIZE = 100`).

**Event types emitted in the system:**

| Type              | Source                          | When                                                                  |
|-------------------|---------------------------------|-----------------------------------------------------------------------|
| `STATE`           | engine                          | Lifecycle transitions, step progress, sensor updates                  |
| `REST`            | api middleware                  | Every non-`/health` HTTP request                                      |
| `SENSOR_REQUEST`  | api middleware                  | `GET /api/dobot/{name}/color\|ir` (reclassified from `REST`)          |
| `EVENT`           | engine                          | `record_external_event()` payloads                                    |
| `KAFKA`           | `KafkaObserver`                 | Every consumed record from observed topics                            |
| `MQTT`            | `MqttPublisher`                 | On each publish (via `DistanceSensor` background task)                |
| `COMMAND`         | engine                          | When a dobot command is dispatched or intercepted                     |
| `PENDING_ACTION`  | engine                          | When an action is added to the pending queue                          |
| `ACTION_RESOLVED` | engine                          | When `resolve_action()` settles a pending action                      |

The operator-focused "process" view filters to `PROCESS_EVENT_TYPES`:
`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`.

### EventBridge

Thin pluggable forwarder defined in `events.py`. Modes:

- `none`  — no-op
- `http`  — POSTs each event payload to the configured URL
- `kafka` — currently a no-op placeholder

> Note: `EventBridge` is **not wired** by `build_dependencies()` in the current
> code. It exists for future use.

> **D2 source:** [`diagrams/06-adapters-events-class.d2`](./diagrams/06-adapters-events-class.d2)

---

## Dependency Wiring

```
main.py
   |
   |  create_app(config_path)
   v
api.py  -- build_dependencies() -->  deps.py
                                       |
                                       +-- EventStore
                                       |
                                       +-- MqttPublisher
                                       |     reads SIMULATOR_BROKER_URL
                                       |
                                       +-- SensorRegistry
                                       |     loads config.yml
                                       |     receives mqtt_publisher
                                       |
                                       +-- ActuatorRegistry
                                       |
                                       +-- InventoryPoller
                                       |     reads INVENTORY_URL
                                       |
                                       +-- SimulationEngine
                                       |     receives: event_store, mqtt_publisher,
                                       |               sensor_registry, actuator_registry
                                       |
                                       +-- KafkaObserver
                                             reads SIMULATED_FACTORY_KAFKA_OBSERVER

api.py also constructs:
   +-- RuntimeSnapshot
         receives: engine, sensor_registry,
                   actuator_registry, inventory_poller, event_store

FastAPI lifespan:
   startup   -> kafka_observer.start()
             -> inventory_poller.start()
   shutdown  -> inventory_poller.stop()
             -> kafka_observer.stop()
```

> **D2 source:** [`diagrams/07-dependency-wiring.d2`](./diagrams/07-dependency-wiring.d2)

---

## Lifecycle

```
                +--------+
   (initial) -->|  IDLE  |<--- reset()
                +--------+<--+
                    |         |
              run_preset()    |  preset
                    |         |  completed
                    v         |
                +--------+    |
                | RUNNING|----+
                +--------+
                    |
            stop() or task cancel
                    |
                    v
                +--------+
                | STOPPED|---- reset() ----> IDLE
                +--------+
```

> **D2 source:** [`diagrams/08-lifecycle.d2`](./diagrams/08-lifecycle.d2)

---

## Preset Execution Flow

```
 1. Client -> POST /api/presets/run        (body: {preset, speed})
 2. API    -> engine.run_preset(name, speed)
 3. Engine:
       - acquire _lock
       - status -> RUNNING, run_id allocated
       - _sensor_registry.reset()
       - emit STATE "Started preset"
       - _sensor_registry.activate() (starts MQTT background tasks)
       - asyncio.create_task(_execute_preset)
 4. For each PresetStep:
       a. If step.awaitRequest is set:
            - _step_gate = (AwaitRequest, asyncio.Event, step)
            - await event.wait() with timeout (delayMs / speed)
            - unblocked when fire_gate_if_matches() matches an incoming
              request; sensor updates applied BEFORE the handler runs
            - on timeout: apply sensorUpdates anyway + emit gate-timeout event
       b. Else:
            - apply step.sensorUpdates via _sensor_registry.apply_updates()
            - sleep(step.delayMs / speed)
       c. Emit a STATE event with step info
 5. After last step:
       - emit STATE "Preset completed"
       - status -> IDLE
       - _sensor_registry.deactivate() (stops MQTT tasks)
       - reset interactive_config to intercept all commands
```

Concurrent path for a request-gated step:

```
Engine (waiting)             Middleware              Engine.fire_gate_if_matches
        |                        |                          |
        |  <--- client request --|                          |
        |                        |--- fire_gate_if_matches->|
        |                        |                          |
        |                        |        apply step's      |
        |                        |        sensorUpdates     |
        | <---------------- event.set() --------------------|
        |                        |                          |
        |                        |  call_next(request)      |
        |                        |  handler reads updated   |
        |                        |  sensor state            |
        v                        v                          v
```

> **D2 source:** [`diagrams/09-preset-sequence.d2`](./diagrams/09-preset-sequence.d2)

---

## Key Design Decisions

| Decision                                                | Rationale                                                                                              |
|---------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| **Monolithic engine**                                   | Single class keeps preset/gate/interactive logic co-located; registries own data, engine owns flow     |
| **Separate registries for sensors and actuators**       | Clean ownership boundaries; each registry is the sole mutator of its data                             |
| **`RuntimeSnapshot` for reads**                         | Composes coherent multi-registry views without the engine needing UI knowledge                         |
| **Plugin-based sensors**                                | New sensor types are added by dropping a module in `sensors/`; type inferred from config or sensor-id  |
| **Plugin-based actuators**                              | `BaseActuator` ABC allows future non-dobot actuators without engine changes                           |
| **`MqttSensor` background tasks**                      | Distance sensors self-publish at a cadence; lifecycle managed by `SensorRegistry.activate/deactivate`  |
| **Request gating**                                      | Preset steps can pause until a matching real HTTP request arrives — enables realistic timing           |
| **In-memory `EventStore`**                              | Bounded `deque` + per-subscriber `asyncio.Queue`s give real-time SSE without external dependencies     |
| **Kafka observer is read-only**                         | Surfaces upstream process-topic activity in the operator UI without ever producing                     |
| **Lazy / no-op MQTT publish**                           | When `SIMULATOR_BROKER_URL` is unset, publishes are no-ops — tests run without a broker                |
| **Standalone `InventoryPoller`**                        | Simple 3s `httpx` poll loop; cancelled cleanly via FastAPI lifespan                                    |

---

## Diagram Index

All diagrams are also provided as [D2](https://d2lang.com) source files in
[`diagrams/`](./diagrams).

| # | File                                                                                  | What it shows                                                          |
|---|---------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| 1 | [`diagrams/01-component.d2`](./diagrams/01-component.d2)                              | Live runtime architecture (external systems + service internals)       |
| 2 | [`diagrams/02-runtime-state.d2`](./diagrams/02-runtime-state.d2)                      | Engine state structure                                                 |
| 3 | [`diagrams/03-engine-class.d2`](./diagrams/03-engine-class.d2)                        | Engine + registries class diagram                                      |
| 4 | [`diagrams/04-sensor-class.d2`](./diagrams/04-sensor-class.d2)                        | Sensor plugin hierarchy and config classes                             |
| 5 | [`diagrams/05-models-class.d2`](./diagrams/05-models-class.d2)                        | API / domain models                                                    |
| 6 | [`diagrams/06-adapters-events-class.d2`](./diagrams/06-adapters-events-class.d2)      | Adapters + `EventStore` + `EventBridge`                                |
| 7 | [`diagrams/07-dependency-wiring.d2`](./diagrams/07-dependency-wiring.d2)              | What `build_dependencies()` actually instantiates                      |
| 8 | [`diagrams/08-lifecycle.d2`](./diagrams/08-lifecycle.d2)                              | Simulation status state machine                                        |
| 9 | [`diagrams/09-preset-sequence.d2`](./diagrams/09-preset-sequence.d2)                  | Preset execution sequence diagram                                      |

Render one with:

```
d2 diagrams/01-component.d2 component.svg
```

or paste any file's contents into <https://play.d2lang.com>.
