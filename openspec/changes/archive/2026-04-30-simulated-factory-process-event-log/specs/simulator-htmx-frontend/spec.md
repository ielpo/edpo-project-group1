## ADDED Requirements

### Requirement: Event-panel filter toggles
The simulator events panel SHALL provide explicit filter toggles for `Full log` and `Process view`.

The selected filter SHALL control which events are rendered without removing any entries from backend full history.

#### Scenario: Operator switches to process view
- **WHEN** the operator selects `Process view` in the events panel
- **THEN** the panel shows only process-relevant event types (`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`)
- **AND** non-process events (for example `REST`, `STATE`, `MQTT`) are hidden from this view

#### Scenario: Operator switches back to full log
- **WHEN** the operator selects `Full log` in the events panel
- **THEN** the panel shows the complete chronological event stream including `MQTT` and other debugging signals

### Requirement: Human-readable process event rendering
In process view, the events panel SHALL render robot command events in a human-readable summary format so operators can quickly follow robot behavior.

The rendering SHALL include action-oriented descriptions for common command types such as move target coordinates, suction cup state, and conveyor movement.

#### Scenario: Move and suction commands are readable
- **WHEN** a command event includes move and suction-cup operations
- **THEN** the panel displays readable command summaries (for example move target coordinates and suction ON/OFF)
- **AND** operators can still inspect raw payload details when needed

### Requirement: Sensor request visibility in process view
The events panel SHALL display `SENSOR_REQUEST` events in process view with clear endpoint context.

#### Scenario: Sensor request appears in process log
- **WHEN** a `SENSOR_REQUEST` event is recorded for color or IR endpoint access
- **THEN** the process view includes the event in chronological order
- **AND** the rendered entry identifies the sensor endpoint that was requested
