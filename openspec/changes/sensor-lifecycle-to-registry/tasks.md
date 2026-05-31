## 1. Extend SensorRegistry with lifecycle state

- [ ] 1.1 Add `mqtt_publisher` parameter to `SensorRegistry.__init__()` and store as `self._mqtt_publisher`
- [ ] 1.2 Add `_live: dict[str, BaseSensor]` field to track active sensor instances
- [ ] 1.3 Add `reset()` method that rebuilds `_live` from `_defaults` (clone + wire)
- [ ] 1.4 Add `get_or_create(sensor_id: str) -> BaseSensor` that returns from `_live` or creates via `make()`, wires if MqttSensor, and inserts into `_live`

## 2. Add lifecycle management methods

- [ ] 2.1 Add `activate()` method that calls `start_task()` on all MqttSensor instances in `_live`
- [ ] 2.2 Add `async deactivate()` method that calls `stop_task()` on all MqttSensor instances in `_live`
- [ ] 2.3 Add `pause()` method that calls `pause_task()` on all MqttSensor instances in `_live`
- [ ] 2.4 Add `resume()` method that calls `resume_task()` on all MqttSensor instances in `_live`
- [ ] 2.5 Add `apply_updates(updates: dict[str, Any])` that updates existing sensors or creates new ones via `get_or_create`

## 3. Add config access methods

- [ ] 3.1 Add `configs() -> list[SensorConfig]` method returning configs for all live sensors
- [ ] 3.2 Add `apply_sensor_update(sensor_id: str, update: dict) -> SensorConfig` for individual sensor updates from API

## 4. Update engine.py to delegate to registry

- [ ] 4.1 Pass `mqtt_publisher` to `SensorRegistry` constructor in engine `__init__`
- [ ] 4.2 Replace `self._sensors` field with `self._sensor_registry` live pool access
- [ ] 4.3 Replace `_wire_sensors()` calls with registry's auto-wiring (remove method)
- [ ] 4.4 Replace `_start_sensor_tasks()` with `self._sensor_registry.activate()`
- [ ] 4.5 Replace `_stop_sensor_tasks()` with `await self._sensor_registry.deactivate()`
- [ ] 4.6 Replace `_pause_sensor_tasks()` with `self._sensor_registry.pause()`
- [ ] 4.7 Replace `_resume_sensor_tasks()` with `self._sensor_registry.resume()`
- [ ] 4.8 Replace `_apply_sensor_updates(step)` with `self._sensor_registry.apply_updates(step.sensorUpdates)`
- [ ] 4.9 Replace `_sensor_for(robot_name, prefix)` with `self._sensor_registry.get_or_create(f"{prefix}-{robot_name}")`
- [ ] 4.10 Remove `MqttSensor` import from engine.py

## 5. Update deps.py wiring

- [ ] 5.1 Pass `mqtt_publisher` to `SensorRegistry` in `build_dependencies()`

## 6. Update tests

- [ ] 6.1 Add unit tests for `SensorRegistry.activate()`, `deactivate()`, `pause()`, `resume()`
- [ ] 6.2 Add unit test for `SensorRegistry.get_or_create()` with both existing and new sensors
- [ ] 6.3 Add unit test for `SensorRegistry.apply_updates()` including lazy creation path
- [ ] 6.4 Update existing engine tests that mock sensor internals to use registry-level mocking
- [ ] 6.5 Run full test suite and fix any regressions
