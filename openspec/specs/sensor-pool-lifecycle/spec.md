# Sensor Pool Lifecycle

Version: v1

## Purpose

Define the contract for `SensorRegistry` lifecycle management. The registry owns the full lifecycle of instantiated sensors — wiring, activation, deactivation, pause/resume, and step-driven updates — behind a single module interface.

## Requirements

### Requirement: Registry manages sensor wiring on creation
The SensorRegistry SHALL automatically wire MQTT publishers to sensors that implement MqttSensor when they are instantiated, eliminating the need for callers to perform a separate wiring step.

#### Scenario: New MQTT sensor is created
- **WHEN** `get_or_create(sensor_id)` is called for a sensor type that implements MqttSensor
- **THEN** the returned sensor instance has its MQTT publisher already wired

#### Scenario: Non-MQTT sensor is created
- **WHEN** `get_or_create(sensor_id)` is called for a sensor type that does not implement MqttSensor
- **THEN** the returned sensor instance is usable without MQTT wiring

### Requirement: Registry starts all sensor background tasks
The SensorRegistry SHALL provide an `activate()` method that starts background publishing tasks for all live MQTT sensors.

#### Scenario: Activate with MQTT sensors
- **WHEN** `activate()` is called on a registry with live MQTT sensors
- **THEN** all MQTT sensors have their background tasks started

#### Scenario: Activate with no live sensors
- **WHEN** `activate()` is called on a registry with no live sensors
- **THEN** no error is raised

### Requirement: Registry stops all sensor background tasks
The SensorRegistry SHALL provide an async `deactivate()` method that stops all running sensor background tasks.

#### Scenario: Deactivate running sensors
- **WHEN** `deactivate()` is called while sensors have active background tasks
- **THEN** all MQTT sensor tasks are stopped

### Requirement: Registry pauses and resumes sensors
The SensorRegistry SHALL provide `pause()` and `resume()` methods that suspend and restore MQTT sensor publishing without destroying the tasks.

#### Scenario: Pause during interactive gating
- **WHEN** `pause()` is called
- **THEN** all MQTT sensors stop publishing until `resume()` is called

#### Scenario: Resume after pause
- **WHEN** `resume()` is called after a prior `pause()`
- **THEN** all MQTT sensors resume publishing

### Requirement: Registry applies step-based sensor updates
The SensorRegistry SHALL provide an `apply_updates(updates: dict)` method that applies sensor value changes from preset steps, lazily creating sensors that do not yet exist.

#### Scenario: Update existing sensor
- **WHEN** `apply_updates({"color-left": "RED"})` is called and `color-left` exists in the live pool
- **THEN** the sensor's value is updated to "RED"

#### Scenario: Update non-existent sensor triggers creation
- **WHEN** `apply_updates({"ir-right": true})` is called and `ir-right` does not exist in the live pool
- **THEN** a new sensor `ir-right` is created, wired, and updated with the value `true`

### Requirement: Registry provides get-or-create by sensor ID
The SensorRegistry SHALL provide a `get_or_create(sensor_id)` method that returns an existing sensor or creates and wires a new one using type inference.

#### Scenario: Sensor already exists
- **WHEN** `get_or_create("color-left")` is called and `color-left` is in the live pool
- **THEN** the existing sensor instance is returned

#### Scenario: Sensor does not exist
- **WHEN** `get_or_create("distance-left")` is called and `distance-left` is not in the live pool
- **THEN** a new sensor is created via `make()`, wired if MQTT, added to the live pool, and returned

### Requirement: Registry resets live pool from defaults
The SensorRegistry SHALL provide a `reset()` method that rebuilds the live sensor pool from configured defaults, discarding any runtime-created sensors.

#### Scenario: Reset after runtime modifications
- **WHEN** `reset()` is called after sensors were lazily created during a run
- **THEN** the live pool contains only the default sensors from config, freshly cloned and wired
