## 1. BaseSensor Interface

- [x] 1.1 Remove `__getattr__` delegation from `BaseSensor`
- [x] 1.2 Change abstract `read()` signature to `read(self, step: int = 0) -> Any` on `BaseSensor`
- [x] 1.3 Add default `clone()` implementation to `BaseSensor` (deep-copy `_cfg`, construct same class)
- [x] 1.4 Add `to_config() -> SensorConfig` to `BaseSensor` (replaces `to_sensor_config()`, returns deep copy of `_cfg`)
- [x] 1.5 Add default `apply_update(data: dict) -> None` to `BaseSensor` (strips `type`, sets matching fields on `_cfg`)
- [x] 1.6 Remove `apply_overrides` from `BaseSensor` — `apply_update` covers both call sites
- [x] 1.7 Keep `to_dict()` fully abstract — no base default

## 2. MqttSensor Interface

- [x] 2.1 Replace `get_topic()` and `get_payload()` on `MqttSensor` with `mqtt_message(self) -> tuple[str, str] | None`
- [x] 2.2 Update `DistanceSensor.mqtt_message()`: return `(self._cfg.mqtt_topic, json.dumps({...}))` using current `_cfg.value`; return `None` if value is `None`
- [x] 2.3 Remove `get_topic()` and `get_payload()` from `DistanceSensor`

## 3. Sensor Plugin Updates

- [x] 3.1 `ColorSensor`: rename `to_sensor_config()` → `to_config()`; rename `apply_update_request()` → `apply_update()`; remove `apply_overrides()` (covered by base `apply_update`); update `read()` to `read(self, step: int = 0)`; remove `value` property
- [x] 3.2 `IrSensor`: rename `to_sensor_config()` → `to_config()`; remove `apply_overrides()` (covered by base); update `read()` to `read(self, step: int = 0)`
- [x] 3.3 `DistanceSensor`: rename `to_sensor_config()` → `to_config()`; rename `apply_update_request()` → `apply_update()`; remove `apply_overrides()` (covered by base); update `read()` to `read(self, step: int = 0)`
- [x] 3.4 `GenericSensor`: add `to_dict()` returning `{"sensorId": self.name, "type": self._cfg.type, "value": self._cfg.value}`; verify `clone()` and `apply_update()` work via base defaults
- [x] 3.5 `DobotColorSensor`: add `to_dict()` returning `{"sensorId": self.name, "type": self._cfg.type, "color": self._cfg.color, "raw_color": self._cfg.raw_color}`; update `read()` to `read(self, step: int = 0)`
- [x] 3.6 Delete `sensors/sensor_loader.py`
- [x] 3.7 Run `tests/test_sensor_plugins.py` — all pass

## 4. MqttPublisher

- [x] 4.1 Rename `adapters/distance_publisher.py` → `adapters/mqtt_publisher.py`
- [x] 4.2 Rename class `DistancePublisher` → `MqttPublisher`
- [x] 4.3 Replace `publish(sensor, distance)` and `_build_payload()` with `async publish_raw(topic: str, payload: str) -> None` — appends MQTT event to store, sends to broker
- [x] 4.4 Update all imports of `DistancePublisher` in `deps.py`, `tests/`

## 5. PresetStep Model and Config Migration

- [x] 5.1 Update `models.py`: rename `PresetStep.publishDistance: float | None` → `triggerMqtt: bool = False`
- [x] 5.2 Migrate `config.yml`: for each of the 9 `publishDistance: <float>` step entries, replace with `triggerMqtt: true` and add the distance value as an explicit `sensorUpdates` entry on the same step

## 6. SensorRegistry

- [x] 6.1 Create `simulated_factory/sensor_registry.py` with `SensorRegistry` class
- [x] 6.2 Implement `SensorRegistry.__init__(config_path)`: load YAML, instantiate default sensors (`_defaults`), store raw preset config
- [x] 6.3 Implement `SensorRegistry.get_presets() -> dict[str, PresetDefinition]`
- [x] 6.4 Implement `SensorRegistry.for_preset(preset: PresetDefinition | None) -> dict[str, BaseSensor]`: clone defaults via `plugin.clone()`, apply preset overrides via `plugin.apply_update()`
- [x] 6.5 Implement `SensorRegistry.make(sensor_id: str, config: dict) -> BaseSensor`: infer type from prefix or explicit `type` field, dynamic import, instantiate plugin
- [x] 6.6 Write unit tests for `SensorRegistry`: default loading, `for_preset` cloning and overrides, `make` with known and unknown types

## 7. Flat SimulationEngine

- [x] 7.1 Create `simulated_factory/engine.py` with flat `SimulationEngine` class
- [x] 7.2 Declare all state as plain instance attributes: `_status`, `_run_id`, `_run_counter`, `_current_preset`, `_current_step`, `_current_step_name`, `_stop_requested`, `_run_task`, `_lock`, `_step_gate`, `_waiting_for_request`, `_pending`, `_pending_counter`, `_interactive_config`, `_sensors`, `_dobots`, `_inventory_cache`, `_inventory_task`, `_inventory_url`
- [x] 7.3 Add module-level `_DEFAULT_INTERCEPTED` frozenset with comment explaining it defaults to full interception so the UI always has control between runs
- [x] 7.4 Implement lifecycle: `get_status()`, `list_presets()`, `run_preset()`, `stop()`, `reset()`
- [x] 7.5 Implement private step loop: `_execute_preset()`, `_run_step()`, `_await_gate()`
- [x] 7.6 Implement `_apply_sensor_updates(step)` — single method used by both gated and non-gated paths
- [x] 7.7 Implement `_publish_mqtt(step)`: skip if `not step.triggerMqtt`; iterate `self._sensors.values()`; for each `isinstance(plugin, MqttSensor)`, call `plugin.mqtt_message()`; if not `None`, call `await self._mqtt_publisher.publish_raw(topic, payload)`
- [x] 7.8 Implement gate API: `fire_gate_if_matches(method, path)` — applies sensor updates synchronously then signals gate event
- [x] 7.9 Implement command handling: `handle_dobot_commands()`, `_apply_dobot_commands()`, `resolve_action()`, `get_pending_actions()`, `get_interactive_config()`, `set_interactive_config()`
- [x] 7.10 Implement sensor API: `get_sensor_configs()` (calls `plugin.to_config()` directly), `update_sensor()` (calls `plugin.apply_update()` directly), `read_color()`, `read_ir()`, `read_color_sensor_bytes()`
- [x] 7.11 Implement dobot and inventory: `get_dobot_state()`, `get_inventory_cache()`, `start_inventory_poller()`, `stop_inventory_poller()`, `_inventory_poll_loop()`
- [x] 7.12 Implement `record_external_event()`

## 8. Wiring and Atomic Cutover

- [x] 8.1 Update `deps.py`: import `MqttPublisher` from `simulated_factory.adapters.mqtt_publisher`; import `SimulationEngine` from `simulated_factory.engine` (module, not package)
- [x] 8.2 Verify `api.py` requires no changes
- [x] 8.3 **Atomic commit**: delete `simulated_factory/engine/` directory and all five files; the new `engine.py` module must land in the same commit — a package and same-named module cannot coexist in Python

## 9. Test Cleanup

- [x] 9.1 `test_engine.py`: confirm `engine._step_gate` and `engine._run_task` are plain attribute access (no property indirection) — no logic change needed
- [x] 9.2 `test_engine.py`: remove any `engine.state` or `engine.sensors` shim usage
- [x] 9.3 `test_twin.py`: update sensor access to use `plugin.to_config()` instead of `plugin.to_sensor_config()`
- [x] 9.4 Update test fixtures that construct `DistancePublisher(None, ...)` to use `MqttPublisher(None, ...)`
- [x] 9.5 Run full test suite (`pytest services/simulated-factory/`) — all pass
