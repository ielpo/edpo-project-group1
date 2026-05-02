# Custom Sensor Plugins

Version: v1

## Purpose

Define the contract for custom sensor plugins in the simulated-factory service, enabling users to extend the simulator with arbitrary sensor types and behaviors through an isolated plugin architecture.

## Requirements

### Requirement: Plugin base interface
All sensor plugins SHALL implement a base interface that defines the methods required for reading, updating, and serializing sensor values. The plugin interface SHALL be defined in `simulated_factory/sensors/base.py` as an abstract base class `BaseSensor` with the following abstract methods: `read()`, `update(value: Any)`, and `to_dict()`.

#### Scenario: Plugin implements required interface
- **WHEN** a developer creates a custom sensor plugin
- **THEN** the plugin class SHALL inherit from `BaseSensor` and implement all three abstract methods
- **AND** the plugin can be instantiated without errors

### Requirement: Plugin registration in configuration
Sensor plugins SHALL be registered in `config.yml` with an explicit `type` field that identifies the plugin module name. The engine SHALL use the `type` field to dynamically import and instantiate the sensor plugin at startup.

#### Scenario: Sensor with explicit type field
- **WHEN** a sensor is defined in `config.yml` with a `type: custom-sensor` field
- **THEN** the engine SHALL attempt to import the plugin from `simulated_factory.sensors.custom_sensor` module
- **AND** the engine SHALL instantiate the plugin class following the naming convention: `CustomSensorSensor` (title-cased type with "Sensor" suffix)

### Requirement: Module organization
Sensor plugins SHALL be organized in the `simulated_factory/sensors/` directory with one plugin per Python file. Each file SHALL contain a single sensor class. Plugin files for custom sensors MAY be added to this directory without modifying the core engine code.

#### Scenario: Custom sensor module placement
- **WHEN** a developer creates a new sensor type called `my-custom-sensor`
- **THEN** the developer SHALL create a file `simulated_factory/sensors/my_custom_sensor.py`
- **AND** that file SHALL contain a class `MyCustomSensorSensor` that inherits from `BaseSensor`

### Requirement: Built-in sensor plugins
Built-in sensors (distance, color, IR) SHALL be implemented as plugins in the `simulated_factory/sensors/` directory, following the same interface and registration rules as custom plugins.

#### Scenario: Built-in distance sensor available
- **WHEN** a sensor is configured with `type: distance`
- **THEN** the engine SHALL load the `DistanceSensor` class from `simulated_factory.sensors.distance`
- **AND** the sensor behaves identically to the original hardcoded implementation

#### Scenario: Built-in color sensor available
- **WHEN** a sensor is configured with `type: color`
- **THEN** the engine SHALL load the `ColorSensor` class from `simulated_factory.sensors.color`
- **AND** the sensor behaves identically to the original hardcoded implementation

#### Scenario: Built-in IR sensor available
- **WHEN** a sensor is configured with `type: ir`
- **THEN** the engine SHALL load the `IrSensor` class from `simulated_factory.sensors.ir`
- **AND** the sensor behaves identically to the original hardcoded implementation

### Requirement: Plugin instantiation with configuration
Sensor plugins SHALL receive their configuration dictionary as a constructor argument during instantiation. The configuration dictionary SHALL contain all sensor fields from `config.yml` including mode, value, scripted_values, cadence_ms, and any custom fields defined for the plugin.

#### Scenario: Plugin receives configuration at instantiation
- **WHEN** a sensor plugin is instantiated
- **THEN** the engine SHALL pass the complete sensor configuration dictionary to the plugin constructor
- **AND** the plugin can access fields like `config['mode']`, `config['value']`, and custom fields

### Requirement: Plugin error handling
If a sensor plugin fails to load (module not found, class not found, instantiation error), the engine SHALL report a clear error message identifying the sensor name, the expected module path, and the failure reason, then SHALL prevent the service from starting.

#### Scenario: Plugin module not found
- **WHEN** a sensor is configured with `type: nonexistent-sensor`
- **THEN** the engine SHALL fail at startup
- **AND** the error message SHALL include the sensor name, expected module path, and the Python error

#### Scenario: Plugin class not found
- **WHEN** a sensor plugin module exists but does not contain the expected class name
- **THEN** the engine SHALL fail at startup
- **AND** the error message SHALL specify the expected class name

### Requirement: Plugin backward compatibility with presets
Sensors implemented as plugins SHALL integrate seamlessly with existing preset definitions and step logic. Preset steps that publish sensor values or override sensors SHALL work with plugin-based sensors exactly as they do with built-in sensors.

#### Scenario: Preset step updates a plugin sensor
- **WHEN** a preset step includes `sensorUpdates` that target a plugin-based sensor
- **THEN** the engine SHALL call the sensor's `update()` method with the provided value
- **AND** subsequent reads of the sensor reflect the updated value

#### Scenario: Preset step publishes a plugin sensor value
- **WHEN** a preset step includes `publishDistance` and the distance sensor is a plugin
- **THEN** the engine SHALL call the sensor's `read()` method and publish the distance value via MQTT

### Requirement: Plugin sensor state isolation
Each sensor plugin instance SHALL maintain its own state independent of other sensors. State from one sensor plugin SHALL NOT leak to or affect other sensors.

#### Scenario: Multiple plugins with independent state
- **WHEN** two custom sensor plugins are instantiated
- **THEN** each plugin SHALL have separate state
- **AND** updating one plugin's state SHALL NOT affect the other
