## 1. Foundation - Base Sensor Interface

- [x] 1.1 Create `simulated_factory/sensors/__init__.py` module directory
- [x] 1.2 Create `simulated_factory/sensors/base.py` with `BaseSensor` abstract base class defining `read()`, `update(value)`, and `to_dict()` abstract methods
- [x] 1.3 Update `SensorConfig` model in `models.py` to include optional `type: str` field (default to inferred type for backward compatibility)

## 2. Extract and Refactor Built-in Sensors

- [x] 2.1 Create `simulated_factory/sensors/distance.py` with `DistanceSensor` class implementing scripted value logic and MQTT publishing behavior
- [x] 2.2 Create `simulated_factory/sensors/color.py` with `ColorSensor` class implementing fixed and raw_color value logic
- [x] 2.3 Create `simulated_factory/sensors/ir.py` with `IrSensor` class implementing fixed boolean sensor logic
- [x] 2.4 Add unit tests for each built-in sensor plugin (test `read()`, `update()`, `to_dict()` methods)
- [x] 2.5 Verify that built-in sensors pass tests with configuration from current `config.yml`

## 3. Engine Refactoring - Plugin Loading

- [x] 3.1 Create `_make_plugin()` method in `SimulationEngine` that iterates sensor configs and instantiates plugins dynamically
- [x] 3.2 Implement plugin discovery logic using `importlib.import_module()` with naming convention: `simulated_factory.sensors.<type>`
- [x] 3.3 Implement class name resolution with title-casing: `<Type>Sensor` (e.g., `type: distance` → `DistanceSensor`)
- [x] 3.4 Add error handling with clear messages for missing modules, missing classes, and instantiation failures
- [x] 3.5 Call plugin loading from `SimulationEngine.reload_config()` before preset loading
- [x] 3.6 Update engine `read_color()`, `read_ir()`, `update_sensor()`, and sensor state access to use plugin instances from `self.sensors` dict
- [x] 3.7 Remove hardcoded sensor initialization logic from `SimulationEngine` (replaced by plugin system)

## 4. Configuration and Backward Compatibility

- [x] 4.1 Add type inference logic to detect sensor type from config keys when `type` field is missing (e.g., `distance-conveyor` → `distance`)
- [x] 4.2 Update `config.yml` schema documentation to include `type` field for all sensors
- [x] 4.3 `PLUGIN_DEVELOPMENT.md` includes migration guide explaining the type field and inference fallback
- [x] 4.4 Test that existing `config.yml` without `type` fields works after type inference (verified via `_TYPE_INFERENCE_RULES`)

## 5. Integration Testing

- [x] 5.1 Run existing engine unit tests to ensure plugin architecture doesn't break current behavior
- [x] 5.2 Run integration tests for presets (happy-path, wrong-color, pickup-failure) to verify sensor updates and publishing still work
- [x] 5.3 Test that MQTT distance publishing works with plugin-based distance sensor
- [x] 5.4 Test that preset sensor_overrides correctly update plugin sensor state

## 6. Documentation and Example

- [x] 6.1 Create `PLUGIN_DEVELOPMENT.md` documenting how to create custom sensors (interface, naming convention, config example)
- [x] 6.2 Create example custom sensor plugin: `simulated_factory/sensors/example_custom.py` with `ExampleCustomSensor` class and inline documentation
- [x] 6.3 Create example config snippet in documentation showing how to register a custom sensor
- [x] 6.4 Document the plugin module naming convention (kebab-case file names → title-case class names)
- [x] 6.5 Add error message examples and troubleshooting section to plugin development guide

## 7. Cleanup and Finalization

- [x] 7.1 Remove any leftover hardcoded sensor references from `engine.py`, `api.py`, and other modules
- [x] 7.2 Run full test suite (unit + integration) to confirm no regressions (97/97 passed)
- [x] 7.3 Update service README.md to mention plugin architecture and link to PLUGIN_DEVELOPMENT.md
- [x] 7.4 Commit with message: `feat(simulated-factory): sensor plugin architecture`
