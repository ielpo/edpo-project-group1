## MODIFIED Requirements

### Requirement: Sensor lifecycle managed through registry
The sensor plugin interface SHALL be consumed exclusively through SensorRegistry lifecycle methods. Callers (such as SimulationEngine) MUST NOT directly call `wire()`, `start_task()`, `stop_task()`, `pause_task()`, or `resume_task()` on individual sensor instances. These remain part of the MqttSensor protocol but are invoked only by the registry.

#### Scenario: Engine starts a simulation run
- **WHEN** the engine starts a preset run
- **THEN** it calls `sensor_registry.activate()` instead of iterating sensors and calling `start_task()` individually

#### Scenario: Engine stops a simulation run
- **WHEN** the engine completes or stops a preset
- **THEN** it calls `sensor_registry.deactivate()` instead of iterating sensors and calling `stop_task()` individually

#### Scenario: Engine pauses during interactive gating
- **WHEN** the engine enters an interactive command gate
- **THEN** it calls `sensor_registry.pause()` instead of iterating sensors and calling `pause_task()` individually
