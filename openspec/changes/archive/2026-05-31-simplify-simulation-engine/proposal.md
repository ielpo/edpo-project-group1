## Why

The simulated-factory engine was refactored into four components (ProcessRunner, ControlPointManager, ResourceManager, SimulationRuntime) to separate concerns, but all four share the same mutable runtime state — making the split nominal rather than real. The result is ~1,433 lines of engine code across five files with duplicated sensor mutation logic, a 411-line facade of one-liner delegations, and backward-compatibility shims that obscure how the simulation actually works. A second problem is hidden: the engine bypasses the `MqttSensor` interface entirely, rebuilding MQTT payloads itself instead of delegating to the sensor. A new developer must read five files, trace cross-component state sharing, and discover the interface bypass before understanding the simulation. The goal is to replace this with an honest, flat design with clear sensor contracts that is easier to onboard, easier to test, and smaller in total.

## What Changes

- **BREAKING** — Delete `engine/runtime.py`, `engine/process_runner.py`, `engine/control_points.py`, `engine/resources.py`, and `engine/__init__.py` (the five-file engine package).
- **BREAKING** — Remove backward-compatibility properties on `SimulationEngine` (`engine.state`, `engine.sensors`, `_MutableStateProxy`).
- **BREAKING** — Rename `BaseSensor.to_sensor_config()` → `to_config()` and `apply_update_request()` → `apply_update()` across all sensor plugins. Remove `apply_overrides()` from the interface — `apply_update()` strips `type` unconditionally, covering both call sites.
- **BREAKING** — `to_dict()` remains fully abstract on `BaseSensor`. No base default is provided — each plugin owns its serialization. Remove `__getattr__` delegation from `BaseSensor`.
- **BREAKING** — `MqttSensor` interface changes: remove `get_topic()` and `get_payload()`, replace with `mqtt_message() -> tuple[str, str] | None`. Sensor returns `(topic, payload)` if it has something to publish, `None` otherwise. Sensor decides; engine just calls.
- **BREAKING** — `PresetStep.publishDistance: float | None` → `PresetStep.triggerMqtt: bool = False` in `models.py`. The float value is no longer meaningful — distance must be set via `sensorUpdates` before the trigger.
- **BREAKING** — `config.yml`: migrate all 9 `publishDistance: <float>` entries to `triggerMqtt: true` plus explicit `sensorUpdates` entries for the distance value.
- **BREAKING** — Rename `DistancePublisher` → `MqttPublisher`. Replace `publish(sensor, distance)` and `_build_payload()` with `publish_raw(topic: str, payload: str)`. The publisher is now a transport layer only — payload construction belongs to the sensor.
- **BREAKING** — Remove `sensors/sensor_loader.py` (unused).
- Replace the five-file engine package with a single `engine.py` containing a flat `SimulationEngine` class with all lifecycle, loop, gate, and command logic.
- Extract sensor loading, cloning, and preset-override logic into a new `sensor_registry.py` with a stateless-after-init `SensorRegistry` (construction only: `for_preset()`, `get_presets()`, `make()`).
- Fix bug: engine `_publish_mqtt()` now uses `isinstance(plugin, MqttSensor)` discovery and calls `plugin.mqtt_message()` on all matching sensors. All `MqttSensor` plugins publish; the engine does not build payloads.
- Extend `BaseSensor` with default implementations of `clone()` and `to_config()`. Mandate `read(step: int = 0)` signature on all plugins.
- Simplify tests: remove proxy-based assertions, update fixtures for `MqttPublisher`.

## Capabilities

### New Capabilities

- `sensor-plugin-interface`: Complete, mandated `BaseSensor` interface — `read(step)`, `update(value)`, `to_dict()` (abstract), `clone()`, `to_config()`, `apply_update(data)` — with default implementations where the base class can provide them. `to_dict()` stays abstract: each plugin owns its serialization contract.

### Modified Capabilities

- `custom-sensor-plugins`: Plugin contract changes — `to_sensor_config()` renamed `to_config()`, `apply_update_request()` renamed `apply_update()`, `apply_overrides()` removed. `__getattr__` delegation removed. `to_dict()` required on all plugins.
- `simulated-factory-service`: Internal engine structure replaced. Preset YAML schema changes: `publishDistance` → `triggerMqtt`. The public HTTP/SSE surface (`api.py`) is unchanged.
- `request-gated-preset-steps`: Gate behavior preserved; implementation moves into the flat engine.
- `interactive-command-gating`: Pending-action and command-interception logic moves into the flat engine.

## Impact

- `services/simulated-factory/simulated_factory/engine/` — deleted entirely.
- `services/simulated-factory/simulated_factory/engine.py` — new flat engine (replaces the package).
- `services/simulated-factory/simulated_factory/sensor_registry.py` — new file.
- `services/simulated-factory/simulated_factory/sensors/base.py` — updated interface; `__getattr__` removed; `MqttSensor.mqtt_message()` replaces `get_topic()` + `get_payload()`.
- `services/simulated-factory/simulated_factory/sensors/*.py` — rename methods, update `read()` signature, add `to_dict()` where missing, implement `mqtt_message()` on `DistanceSensor`.
- `services/simulated-factory/simulated_factory/sensors/sensor_loader.py` — deleted.
- `services/simulated-factory/simulated_factory/models.py` — `PresetStep.publishDistance` → `triggerMqtt`.
- `services/simulated-factory/simulated_factory/adapters/distance_publisher.py` — renamed to `mqtt_publisher.py`; class renamed `MqttPublisher`; simplified to `publish_raw(topic, payload)`.
- `services/simulated-factory/simulated_factory/deps.py` — simplified construction, updated import.
- `services/simulated-factory/config.yml` — migrate 9 `publishDistance` step entries.
- `services/simulated-factory/tests/` — remove proxy assertions, update fixtures.
- No change to `api.py`, `events.py`, or `adapters/kafka_observer.py`.
