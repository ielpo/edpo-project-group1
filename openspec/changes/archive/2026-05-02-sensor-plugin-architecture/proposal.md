## Why

The simulated-factory service currently has sensors hardcoded in the engine logic with fixed implementations for distance, color, and IR sensors. This creates friction when adding new sensor types or customizing sensor behavior for specific test scenarios. A plugin architecture would enable users to define custom sensors as isolated Python modules, configured explicitly in `config.yml`, making the system more extensible and maintainable without requiring code changes to the core engine.

## What Changes

- **Refactor sensor initialization**: Move sensor instantiation from engine-level hardcoding to a plugin loading mechanism that reads sensor definitions from `config.yml`
- **Create plugin interface**: Define a base `Sensor` class that all sensor plugins must implement (read, update, serialize methods)
- **Establish plugins directory**: Create `simulated_factory/sensors/` for built-in and plugin sensors; each sensor type gets its own `.py` file
- **Explicit registration**: Sensors are registered in `config.yml` with their `type` and optional constructor parameters
- **Separate built-in and custom**: Core sensors (distance, color, IR) remain as built-in plugins; users can add custom sensors alongside them
- **Update config schema**: Modify `config.yml` structure to support plugin registration without breaking existing preset definitions

## Capabilities

### New Capabilities

- `custom-sensor-plugins`: Users can now create custom sensor plugins by writing a Python class that extends the sensor base interface and registering it in `config.yml`. Each plugin is an isolated module in `simulated_factory/sensors/`, allowing arbitrary sensor types and behaviors to be added without modifying the core engine.

### Modified Capabilities

- `simulated-factory-service`: The sensor configuration schema in `config.yml` changes to support plugin registration (e.g., adding `type: color` to identify the plugin), but the HTTP API and preset execution behavior remain unchanged. This is an internal implementation refactor with no breaking changes to external contracts.

## Impact

- **Code**: Primarily `simulated_factory/engine.py` (sensor loading logic), `simulated_factory/models.py` (sensor config structure), and addition of new `simulated_factory/sensors/` directory
- **Configuration**: `config.yml` gains `type` field for each sensor to specify the plugin; existing preset and step definitions remain compatible
- **Dependencies**: No new external dependencies; uses only Python standard library and existing imports
- **Testing**: Existing unit tests for engine behavior should remain valid; new tests cover plugin loading and custom sensor implementations
- **Other services**: No impact on other services (color-sensor, inventory, order, etc.); this is isolated to simulated-factory
