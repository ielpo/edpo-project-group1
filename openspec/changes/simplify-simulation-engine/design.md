## Context

The simulated-factory engine was split into four components (ProcessRunner, ControlPointManager, ResourceManager, SimulationRuntime) during a prior refactor. The intent was to separate concerns, but all components receive the same four runtime dataclass slices in their constructors and freely read/write each other's "owned" domains: ProcessRunner modifies `ControlState`, ControlPointManager reads `process.current_step` and `factory.run_id`, ResourceManager uses a callback to get the current step from ProcessRunner. The result is nominal separation with real coupling — and 1,433 lines across five files to express a simulation that is conceptually straightforward.

A second problem exists independently: `_publish_distance_if_needed` in `process_runner.py` bypasses the `MqttSensor` interface entirely. It calls `to_sensor_config()` to get the config, then rebuilds the MQTT payload itself inside `DistancePublisher._build_payload()`. `DistanceSensor.get_topic()` and `get_payload()` are never called. The interface is present but ignored, which is worse than no interface — it promises a contract that the engine does not honour.

## Goals / Non-Goals

**Goals:**
- Replace five engine files with two (`engine.py`, `sensor_registry.py`) with no loss of functional behavior.
- Make the `BaseSensor` interface complete and mandatory — eliminating all duck-typing fallbacks from the engine.
- Fix the `MqttSensor` bypass bug: engine discovers sensors via `isinstance` and triggers publishing via the interface.
- Make engine state accessible as plain attributes in tests — removing proxy objects and backward-compat shims.
- Preserve the unchanged public HTTP/SSE surface: all method signatures consumed by `api.py` stay the same.

**Non-Goals:**
- No change to `api.py`, `events.py`, or the Kafka adapter.
- No change to gate behavior or sensor config file format (other than `publishDistance` → `triggerMqtt`).
- No new user-facing features or API endpoints.

## Decisions

### 1. Flatten the engine into one class, not four

`SimulationEngine` becomes a single flat class in `engine.py`. All lifecycle, step loop, gate, pending-action, dobot command, and sensor-read logic lives here. The four components and the runtime dataclasses are deleted.

**Why:** The components all share the same mutable state anyway — splitting them added indirection without reducing coupling. A flat class makes the execution trace linear: one file, top to bottom, with labelled sections replacing the file-per-concern structure. For onboarding, there is no architecture diagram to misread.

**Alternative considered:** Keep two components (loop + commands) and one data holder. Rejected because the gate and command logic are inherently coupled — a gated step waits for an HTTP request, which also goes through command interception. Splitting them requires cross-component coordination that is harder to follow than co-location.

### 2. Extract sensors into a stateless `SensorRegistry` — construction only

`SensorRegistry` owns config loading, plugin instantiation, cloning, and preset override application. Its public interface is three methods: `for_preset(preset)`, `get_presets()`, and `make(sensor_id, config)`. It does not hold the active sensor dict and has no `configs()` or `update()` methods.

The engine owns `self._sensors` and operates on it directly: `plugin.to_config()` for reads, `plugin.apply_update()` for updates. Passing the active dict back into the registry would create a false dependency — the registry's value is construction, not runtime mutation.

**Why stateless-after-init:** Removes the `set_current_step_getter` callback hack. The engine passes `self._current_step` directly when calling `plugin.read(self._current_step)`.

### 3. Mandate a complete `BaseSensor` interface; `to_dict()` fully abstract

`BaseSensor` provides default implementations for `clone()` (deep-copy config, construct same class) and `to_config()` (return deep copy of `_cfg`). `read(step: int = 0)`, `update(value)`, and `to_dict()` remain abstract.

`to_dict()` has no base default. Each plugin owns its serialization — different config shapes (e.g., `DobotColorSensorConfig` has `color` + `raw_color`, not `value`) mean a generic default would either expose internal fields or fail silently. Forcing plugins to be explicit makes the API response contract visible in the plugin file.

`apply_update(data)` replaces both `apply_update_request()` and `apply_overrides()`. It strips `type` unconditionally — the only call site that ever included `type` was the YAML config path. One method is simpler than two near-identical ones.

`__getattr__` delegation on `BaseSensor` is removed. Code outside a plugin accesses sensor state only through `read()`, `to_config()`, and `to_dict()`.

**Breaking change accepted:** Renames and interface extension are intentional. All five in-tree plugins are updated as part of this change.

### 4. Fix `MqttSensor`: `mqtt_message() -> tuple[str, str] | None`

`MqttSensor` interface is redesigned. `get_topic()` and `get_payload()` are replaced by a single `mqtt_message() -> tuple[str, str] | None`. The sensor returns `(topic, payload)` if it has something to publish based on its current config, or `None` to skip. The engine does not build payloads.

Engine trigger path:
```python
for plugin in self._sensors.values():
    if isinstance(plugin, MqttSensor):
        msg = plugin.mqtt_message()
        if msg is not None:
            topic, payload = msg
            await self._mqtt_publisher.publish_raw(topic, payload)
```

**Why:** The previous implementation bypassed the interface and rebuilt the payload inside `DistancePublisher`. This is a bug — the interface existed but was ignored. Shape 1 (sensor returns data, engine publishes) is preferred over having the sensor call the publisher directly, because sensors remain pure data objects with no IO dependency. Sensor tests need no mock publisher.

### 5. `publishDistance` → `triggerMqtt: bool`

`PresetStep.publishDistance: float | None` is renamed to `triggerMqtt: bool = False` in `models.py`. The step field is now a pure trigger. Sensor values must be set via `sensorUpdates` before the trigger step. The engine calls `_publish_mqtt(step)` when `step.triggerMqtt` is true.

`config.yml` has 9 affected entries. Each `publishDistance: <float>` entry migrates to `triggerMqtt: true` plus an explicit `sensorUpdates` entry for the distance value.

**Why:** A float field named `publishDistance` implies the value is used. In the pure trigger model it is not — the sensor reads from its own `_cfg`. Keeping the float creates a false affordance that will confuse preset authors. An honest rename costs a one-time migration.

### 6. `DistancePublisher` → `MqttPublisher`

`adapters/distance_publisher.py` is renamed `adapters/mqtt_publisher.py`. The class is renamed `MqttPublisher`. The `publish(sensor, distance)` method and `_build_payload()` are removed. The single public method is `publish_raw(topic: str, payload: str)`, which appends to the event store and sends to the broker.

**Why:** Payload construction now belongs to the sensor via `mqtt_message()`. The publisher is a transport layer. The old name and interface implied distance-specific knowledge the class no longer needs.

### 7. Remove all backward-compat shims from the engine

`_MutableStateProxy`, `engine.state`, and `engine.sensors` are deleted. Tests access `engine._step_gate` and `engine._run_task` as plain attributes — the same names as the backward-compat properties, so no test logic changes.

**Why:** Shims exist to avoid breaking callers when internals change. Since compatibility is broken deliberately, the shims have no remaining purpose.

### 8. `_DEFAULT_INTERCEPTED` stays as a module-level constant

The frozenset of six command types intercepted by default between runs stays in `engine.py` as a module-level constant. A one-line comment explains the intent: interactive mode defaults to intercepting all known dobot command types after each run, so the UI always has control without explicit configuration.

**Why:** The behavior is intentional and correct. The comment makes it visible to new developers without moving it to config.

## Risks / Trade-offs

- [One class file with all engine logic] → Flat is not the same as large. Section comments (`# --- Step loop ---`, `# --- Gates ---`, etc.) provide the same navigational structure as separate files. The file will be smaller than `engine/__init__.py` alone was.
- [Breaking sensor interface may miss a plugin] → All five plugins are in-tree and enumerated in the task list. Each is updated explicitly.
- [config.yml migration requires updating distance values] → Nine entries. Each needs a `sensorUpdates` entry added and `publishDistance` replaced. Covered in tasks.
- [Sensor config format is unchanged, dynamic import path is not] → `SensorRegistry.make()` uses the same `simulated_factory.sensors.<type>` dynamic import pattern as `ResourceManager._make_plugin()`. No config migration needed beyond `publishDistance` → `triggerMqtt`.

## Migration Plan

The change is contained entirely within `services/simulated-factory/`. No other services are affected. Implementation order:

1. Update `BaseSensor` interface and all sensor plugins. Sensor plugin tests pass independently after this step.
2. Update `MqttSensor` interface (`mqtt_message()`), update `DistanceSensor`. Rename `DistancePublisher` → `MqttPublisher`.
3. Update `PresetStep` model (`triggerMqtt`). Migrate `config.yml`.
4. Write `SensorRegistry`. Verify sensor-config and preset-loading coverage passes.
5. Write flat `engine.py`. Update `deps.py`. Run full test suite.
6. **Atomic commit**: delete `engine/` package directory and create `engine.py` in the same commit. A Python package and a same-named module cannot coexist — this transition must be a single atomic change.
7. Simplify tests — remove proxy assertions, update fixtures.
8. Delete `sensor_loader.py`.

Each step except step 6 can be committed independently.

## Open Questions

- Should `SensorRegistry.make()` be public or private? It is called by the engine when `update_sensor()` requests a sensor not in defaults. Recommendation: keep it public since the engine needs to call it. Name it `make(sensor_id, config)`.
