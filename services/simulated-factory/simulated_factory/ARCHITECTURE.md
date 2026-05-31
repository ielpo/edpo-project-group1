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
4. [Sensor Plugin System](#sensor-plugin-system)
5. [API / Domain Models](#api--domain-models)
6. [Adapters & Events](#adapters--events)
7. [Dependency Wiring](#dependency-wiring)
8. [Lifecycle](#lifecycle)
9. [Preset Execution Flow](#preset-execution-flow)
10. [Key Design Decisions](#key-design-decisions)
11. [Diagram Index](#diagram-index)

---

## System Overview

The diagram below shows the *live* runtime architecture. Two modules present
in the tree are intentionally omitted because nothing in the running system
wires them up: `sensors/sensor_loader.py` (`load_sensor()` is never called —
`ResourceManager` does its own dynamic import) and
`adapters/mqtt_publisher.py` (`MqttPublisher` is never instantiated by
`build_dependencies()`).

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
   |   +---------------- SimulationEngine (facade) ----------------+             |
   |   +------+--------------+--------------+---------------------+             |
   |          |              |              |                                    |
   |          v              v              v                                    |
   |    ProcessRunner   ControlPoint     ResourceManager                         |
   |                    Manager                                                  |
   |          \             |              /                                     |
   |           \            v             /                                      |
   |            +--> SimulationRuntime <-+                                       |
   |                (factory / process /                                         |
   |                 control / resources)                                        |
   |                                                                             |
   |   Sensor plugins (color, ir, distance, generic, dobot_color)                |
   |                                                                             |
   |   +---- Adapters ----+        +----- Events -----+                          |
   |   |  KafkaObserver   |        |   EventStore     | <-- SSE subscribers      |
   |   |  DistancePub     |        |   EventBridge    | --> optional HTTP relay  |
   |   +--+------------+--+        +------------------+                          |
   +------|------------|---------------------------------------------------------+
          |            |
          |            +-------------- MQTT publish ---------------> (MQTT)
          +------------- consumes Kafka topics ----------------------- (Kafka)
```

> **D2 source:** [`diagrams/01-component.d2`](./diagrams/01-component.d2)

---

## Component Inventory

| Layer    | Component                | File                                    | Responsibility                                                       |
|----------|--------------------------|-----------------------------------------|----------------------------------------------------------------------|
| API      | FastAPI app + middleware | `api.py`                                | HTTP/SSE surface, request capture, HTMX fragments                    |
| API      | Dependency wiring        | `deps.py`                               | Builds EventStore, EventBridge, DistancePublisher, Engine, Observer  |
| Engine   | SimulationEngine         | `engine/__init__.py`                    | Facade exposing the engine API; delegates to sub-managers            |
| Engine   | ProcessRunner            | `engine/process_runner.py`              | Preset loading, step advancement, step side-effects                  |
| Engine   | ControlPointManager      | `engine/control_points.py`              | Request gates, pending actions, command interception                 |
| Engine   | ResourceManager          | `engine/resources.py`                   | Sensor lifecycle, dobot state reads, inventory polling               |
| Engine   | SimulationRuntime        | `engine/runtime.py`                     | Mutable runtime state (factory / process / control / resources)      |
| Sensors  | BaseSensor + plugins     | `sensors/`                              | Pluggable sensor implementations                                     |
| Adapters | DistancePublisher        | `adapters/distance_publisher.py`        | MQTT publish of distance readings                                    |
| Adapters | KafkaObserver            | `adapters/kafka_observer.py`            | Read-only Kafka consumer feeding the event store                     |
| Events   | EventStore               | `events.py`                             | In-memory event log + pub/sub queues for SSE                         |
| Events   | EventBridge              | `events.py`                             | Optional HTTP relay of events to external systems                    |
| Models   | Pydantic + dataclasses   | `models.py`                             | API + domain shapes                                                  |
| Utils    | Utility functions        | `utils.py`                              | Path-pattern regex, color helpers, broker parsing                    |

**Inactive code (present in the tree but not wired at runtime):**

| Module                          | Status                                                                          |
|---------------------------------|---------------------------------------------------------------------------------|
| `sensors/sensor_loader.py`      | `load_sensor()` function — never imported. `ResourceManager` loads plugins itself. |
| `adapters/mqtt_publisher.py`    | `MqttPublisher` class — never instantiated by `build_dependencies()`.           |

---

## Engine — Core Domain

The engine is one facade plus three focused managers. The managers share
references to a single mutable `SimulationRuntime` instead of keeping their
own copies of state.

### Subcomponent roles

| Component             | Owns                                | Drives                                                                      |
|-----------------------|-------------------------------------|-----------------------------------------------------------------------------|
| `SimulationEngine`    | runtime + all managers              | Exposes the public engine API; assembles the rest at construction time      |
| `ProcessRunner`       | (holds refs only)                   | Preset task lifecycle, step sleeping, distance publish                      |
| `ControlPointManager` | (holds refs only)                   | Gate matching, command interception, pending action resolution              |
| `ResourceManager`     | sensor plugins, inventory poll task | Config loading, sensor instantiation, dobot reads, inventory polling        |

### Runtime state structure

```
SimulationRuntime
|
+-- FactoryState        run_id, status, current_preset, run_counter,
|                       stop_requested, run_task, lock
|
+-- ProcessState        current_step, current_step_name, presets
|
+-- ControlState        step_gate, waiting_for_request,
|                       interactive_config, pending, pending_counter
|
+-- PhysicalResources   default_sensors, sensors, dobots,
                        inventory_cache, inventory_poll_task
```

State flow: `FactoryState` drives the run lifecycle → `ProcessState` advances
through preset steps → `ControlState` holds the gate the runner is waiting on
→ when the gate fires, sensor updates land in `PhysicalResources` so the
triggering request observes them.

> **D2 source:** [`diagrams/02-runtime-state.d2`](./diagrams/02-runtime-state.d2)

### Class APIs

#### `SimulationEngine` (facade)

| Method                                                   | Returns                  | Purpose                                                       |
|----------------------------------------------------------|--------------------------|---------------------------------------------------------------|
| `get_status()`                                           | `SimulationState`        | Snapshot of current run/state                                 |
| `list_presets()`                                         | `list`                   | Available preset definitions                                  |
| `run_preset(name, speed)`                                | `str` (run_id)           | Start a preset run                                            |
| `stop()`                                                 | —                        | Request stop on the current run                               |
| `reset()`                                                | —                        | Cancel current run, reset runtime                             |
| `fire_gate_if_matches(method, path)`                     | `bool`                   | Trigger the preset step gate if it matches                    |
| `handle_dobot_commands(robot, payload)`                  | `dict`                   | Execute or intercept dobot commands                           |
| `resolve_action(id, outcome, reason)`                    | `PendingAction`          | Resolve a pending intercepted action                          |
| `get_pending_actions()`                                  | `list`                   | Currently waiting actions                                     |
| `get_interactive_config()` / `set_interactive_config()`  | `InteractiveConfig`      | Interactive interception config                               |
| `get_sensor_configs()`                                   | `list[SensorConfig]`     | All configured sensors                                        |
| `update_sensor(id, update)`                              | `SensorConfig`           | Apply mode/value update to a sensor                           |
| `read_color(robot)`                                      | `tuple[str, list[int]]`  | Color sensor read                                             |
| `read_ir(robot)`                                         | `bool`                   | IR sensor read                                                |
| `read_color_sensor_bytes()`                              | `dict`                   | RGB-byte view of the left color sensor                        |
| `get_dobot_state(robot)`                                 | `DobotRuntimeState`      | Snapshot of a dobot                                           |
| `get_inventory_cache()`                                  | `dict`                   | Latest polled inventory snapshot                              |
| `start_inventory_poller()` / `stop_inventory_poller()`   | —                        | Inventory poll task lifecycle                                 |
| `record_external_event(payload)`                         | —                        | Inject an external event into `EventStore`                    |

**Backward-compat surface:** `state` (returns a `_MutableStateProxy` so legacy
tests can mutate engine state directly), `sensors`, `presets`,
`interactive_config`, `_step_gate`, `_run_task`, `_inventory_cache`.

#### `ProcessRunner`

| Public method                | Notes                                                                          |
|------------------------------|--------------------------------------------------------------------------------|
| `list_presets()`             | Preset summaries `[{name, description, steps:[{name}]}]`                       |
| `run_preset(name, speed)`    | Creates the `_execute_preset` task; raises `KeyError` / `RuntimeError`         |

Internal: `_execute_preset`, `_await_step_gate`, `_apply_step_side_effects_sync`,
`_publish_distance_if_needed`, `_clear_step_gate`, `_record_event`.

#### `ControlPointManager`

| Public method                                            | Notes                                                            |
|----------------------------------------------------------|------------------------------------------------------------------|
| `fire_gate_if_matches(method, path)`                     | Apply step side-effects then signal the runner                   |
| `matches_gate(method, path)`                             | Read-only: is there a gate that matches?                         |
| `handle_dobot_commands(robot, payload)`                  | Execute or intercept based on interactive config                 |
| `resolve_action(action_id, outcome, reason)`             | Resolve a waiting action                                         |
| `get_pending_actions()`                                  | Public view of `control.pending`                                 |
| `get_interactive_config()` / `set_interactive_config()`  | Interactive mode settings                                        |

> *Original diagrams labelled this `resolve_pending_action()`; the actual
> method is `resolve_action()`.*

#### `ResourceManager`

| Public method                                            | Notes                                                            |
|----------------------------------------------------------|------------------------------------------------------------------|
| `get_presets()`                                          | Parsed `PresetDefinition`s from config                           |
| `sensors()`                                              | Return a fresh clone of all default sensors                      |
| `get_sensor_configs()`                                   | Sorted list of current sensor configs                            |
| `update_sensor(id, update)`                              | Apply update + emit STATE event                                  |
| `read_color(robot)` / `read_ir(robot)`                   | Sensor reads (auto-creates plugin if missing)                    |
| `read_color_sensor_bytes()`                              | RGB bytes for the left color sensor                              |
| `get_dobot_state(robot)`                                 | Snapshot of a dobot state                                        |
| `make_plugin(id, cfg)`                                   | Public access to plugin instantiation                            |
| `set_current_step_getter(getter)`                        | Wire the engine's step getter for step-aware sensors             |
| `get_inventory_cache()`                                  | Latest inventory snapshot                                        |
| `start_inventory_poller()` / `stop_inventory_poller()`   | Poll task lifecycle                                              |

> **D2 source (full class diagram including runtime sub-states):**
> [`diagrams/03-engine-class.d2`](./diagrams/03-engine-class.d2)

---

## Sensor Plugin System

### Plugin discovery

`ResourceManager._make_plugin(sensor_id, config)` performs dynamic loading:

1. Infer the plugin type from `config["type"]`, or fall back to a sensor-id
   prefix rule (`color-*` → `color`, `ir-*` → `ir`, `distance-*` → `distance`,
   anything else → `generic`).
2. Import `simulated_factory.sensors.<type>` and look up `<Type>Sensor` and
   optionally `<Type>SensorConfig`.
3. Build a config instance (typed if a `*Config` class exists, otherwise a
   plain `SensorConfig`).
4. Instantiate `<Type>Sensor(sensor_id, cfg)`.

Sensors are cloned from defaults on each preset start so step-level updates do not mutate the default plugins.

> Note: `sensors/sensor_loader.py` exposes a standalone `load_sensor()` helper
> that is **not used** by the running system. Treat it as legacy unless the
> intent is to consolidate plugin loading later.

### Built-in plugins

| Type          | Class               | Read returns             | Config highlights                                                          |
|---------------|---------------------|--------------------------|----------------------------------------------------------------------------|
| `color`       | `ColorSensor`       | `tuple[str, list[int]]`  | `mode`, `value`, `raw_color`, `scripted_values`                            |
| `ir`          | `IrSensor`          | `bool`                   | `mode`, `value`, `scripted_values`                                         |
| `distance`    | `DistanceSensor`*   | `float`                  | `mode`, `value`, `mqtt_topic`, `uid`, `location`, `cadence_ms`             |
| `generic`     | `GenericSensor`     | `Any`                    | Fallback for unrecognized types                                            |
| `dobot_color` | `DobotColorSensor`  | `tuple[str, list[int]]`  | Color readings tied to a dobot                                             |

*`DistanceSensor` also implements `MqttSensor` (`get_topic()` / `get_payload()`).

### Plugin interface

```
BaseSensor (ABC)
   +name: str
   -_cfg: SensorConfig
   +read()                  (abstract)
   +update(value)           (abstract)
   +to_dict()               (abstract)

MqttSensor (ABC mix-in)
   +get_topic()             (abstract)
   +get_payload()           (abstract)
```

Concrete plugins also commonly offer: `to_sensor_config()`, `clone()`,
`apply_overrides(overrides)`, `apply_update_request(update)`. `ResourceManager`
uses these when available and falls back to attribute manipulation otherwise.

> **D2 source:** [`diagrams/04-sensor-class.d2`](./diagrams/04-sensor-class.d2)

---

## API / Domain Models

### Live state

| Model               | Kind     | Purpose                                                                |
|---------------------|----------|------------------------------------------------------------------------|
| `SimulationStatus`  | enum     | `IDLE` / `RUNNING` / `STOPPED`                                         |
| `SimulationState`   | pydantic | Snapshot returned by `get_status()`                                    |
| `DobotRuntimeState` | pydantic | Per-dobot pose, suction, conveyor state                                |
| `Position`          | pydantic | `x, y, z, r`                                                           |
| `AwaitRequest`      | pydantic | `method, path` pair used by gates                                      |

### Preset definitions

| Model               | Kind     | Purpose                                                                |
|---------------------|----------|------------------------------------------------------------------------|
| `PresetDefinition`  | pydantic | `name, description, steps[]`                                           |
| `PresetStep`        | pydantic | `name, delayMs, note?, publishDistance?, sensorUpdates, awaitRequest?` |

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
| `DistancePublisher` | yes                 | service → MQTT         | Always appends an `MQTT` event; only publishes if `SIMULATOR_BROKER_URL` is set and `paho.mqtt` is importable |
| `KafkaObserver`     | yes                 | Kafka → service        | Read-only; appends `KAFKA` events. Failures are non-fatal                                  |
| `EventBridge`       | yes                 | service → External     | Modes: `none` (default), `http` (POST to `SIMULATOR_EVENT_BRIDGE_URL`), `kafka` (no-op stub)|
| `MqttPublisher`     | **no**              | (unused at runtime)    | Standalone class in `adapters/mqtt_publisher.py` — not instantiated anywhere                |

### EventStore

In-memory bounded `deque` (default `max_entries=500`) plus a set of subscriber
`asyncio.Queue`s. Each appended event is delivered to subscribers via
`put_nowait`, dropping when a queue is full (subscriber queue size is
`EVENT_SUBSCRIBER_QUEUE_SIZE = 100`).

**Event types emitted in the system:**

| Type              | Source                                       | When                                                                  |
|-------------------|----------------------------------------------|-----------------------------------------------------------------------|
| `STATE`           | engine                                       | Lifecycle transitions, step progress, sensor updates                  |
| `REST`            | api middleware                               | Every non-`/health` HTTP request                                      |
| `SENSOR_REQUEST`  | api middleware                               | `GET /api/dobot/{name}/color\|ir` (reclassified from `REST`)          |
| `EVENT`           | engine                                       | `record_external_event()` payloads                                    |
| `KAFKA`           | `KafkaObserver`                              | Every consumed record from observed topics                            |
| `MQTT`            | `DistancePublisher` (and `MqttPublisher` if wired) | On each publish                                                  |
| `COMMAND`         | `ControlPointManager`                        | When a dobot command is dispatched or intercepted                     |
| `PENDING_ACTION`  | `ControlPointManager`                        | When an action is added to the pending queue                          |
| `ACTION_RESOLVED` | `ControlPointManager`                        | When `resolve_action()` settles a pending action                      |

The operator-focused "process" view filters to `PROCESS_EVENT_TYPES`:
`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`.

### EventBridge

Thin pluggable forwarder. Modes:

- `none`  — no-op
- `http`  — POSTs each event payload to the configured URL
- `kafka` — currently a no-op placeholder

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
                                       +-- EventBridge
                                       |     reads SIMULATOR_EVENT_BRIDGE
                                       |     and  SIMULATOR_EVENT_BRIDGE_URL
                                       |
                                       +-- DistancePublisher
                                       |     reads SIMULATOR_BROKER_URL
                                       |
                                       +-- SimulationEngine
                                       |     internally constructs:
                                       |       ResourceManager
                                       |       ProcessRunner
                                       |       ControlPointManager
                                       |       SimulationRuntime
                                       |
                                       +-- KafkaObserver
                                             reads SIMULATED_FACTORY_KAFKA_OBSERVER

FastAPI lifespan:
   startup   -> kafka_observer.start()
             -> engine.start_inventory_poller()
   shutdown  -> engine.stop_inventory_poller()
             -> kafka_observer.stop()
```

> **D2 source:** [`diagrams/07-dependency-wiring.d2`](./diagrams/07-dependency-wiring.d2)

> Note: `MqttPublisher` and `sensor_loader.load_sensor()` exist in the tree
> but are **not** instantiated or called by `build_dependencies()`.

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
 2. API    -> SimulationEngine.run_preset(name, speed)
 3. Engine -> ProcessRunner.run_preset(name, speed)
                - acquire factory.lock
                - status -> RUNNING, run_id allocated
                - emit STATE "Started preset"
                - asyncio.create_task(_execute_preset)
 4. For each PresetStep:
       a. If step.awaitRequest is set:
            - control.step_gate = (AwaitRequest, asyncio.Event, step)
            - await event.wait() (optional timeout)
            - unblocked when ControlPointManager.fire_gate_if_matches()
              matches an incoming request; sensor updates applied
              synchronously BEFORE the handler reads sensors
       b. Else:
            - apply step.sensorUpdates to plugins
            - if step.publishDistance: DistancePublisher.publish(...) -> MQTT
            - sleep(step.delayMs / speed)
       c. Emit a STATE event with step info
 5. After last step:
       - emit STATE "Preset completed"
       - status -> IDLE, run_task cleared
```

Concurrent path for a request-gated step:

```
ProcessRunner                Middleware              ControlPointManager
    (waiting)                    |                          |
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
| **Facade pattern** (`SimulationEngine`)                 | Single stable entry point for API and tests; delegates to three focused managers                       |
| **Dataclass runtime vs. Pydantic snapshots**            | Mutable internal `SimulationRuntime` stays decoupled from API-facing immutable `SimulationState`       |
| **Plugin-based sensors**                                | New sensor types are added by dropping a module in `sensors/`; type inferred from config or sensor-id  |
| **Request gating**                                      | Preset steps can pause until a matching real HTTP request arrives — enables realistic timing           |
| **In-memory `EventStore`**                              | Bounded `deque` + per-subscriber `asyncio.Queue`s give real-time SSE without external dependencies     |
| **Kafka observer is read-only**                         | Surfaces upstream process-topic activity in the operator UI without ever producing                     |
| **DistancePublisher via MQTT**                          | Emulates Tinkerforge-style distance messages consumed by downstream services                           |
| **`_MutableStateProxy` compatibility shim**             | Lets legacy tests mutate `engine.state.*` directly while real state lives in `SimulationRuntime`       |
| **Lazy / no-op MQTT publish**                           | When `SIMULATOR_BROKER_URL` is unset, publishes are no-ops — tests run without a broker                |
| **Inventory poller inside `ResourceManager`**           | Simple 3s `httpx` poll loop; cancelled cleanly via FastAPI lifespan                                    |

---

## Diagram Index

All diagrams are also provided as [D2](https://d2lang.com) source files in
[`diagrams/`](./diagrams).

| # | File                                                                                  | What it shows                                                          |
|---|---------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| 1 | [`diagrams/01-component.d2`](./diagrams/01-component.d2)                              | Live runtime architecture (external systems + service internals)       |
| 2 | [`diagrams/02-runtime-state.d2`](./diagrams/02-runtime-state.d2)                      | Substructures of `SimulationRuntime`                                   |
| 3 | [`diagrams/03-engine-class.d2`](./diagrams/03-engine-class.d2)                        | Engine facade + managers + runtime sub-states                          |
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
