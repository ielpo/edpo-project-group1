## MODIFIED Requirements

### Requirement: Explicit sensor type selection with backward compatibility
The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted. Built-in sensor defaults MUST store only the current manual value and sensor-specific static metadata; `mode` and `scripted_values` MUST NOT be part of the sensor default contract.

#### Scenario: Sensor type is declared explicitly
- **WHEN** a sensor is configured with `type: color`
- **THEN** the service uses the color sensor implementation for that sensor
- **AND** the sensor default stores its manual `value`, optional `raw_color`, and static metadata without a configured mode field

#### Scenario: Existing sensor config without type still works
- **WHEN** an existing configuration defines `color-left` without an explicit `type`
- **THEN** the service infers the sensor type from the sensor id prefix
- **AND** the sensor default remains usable without legacy `mode` or `scripted_values` fields

### Requirement: Sensor configuration management
The service MUST provide `GET /api/config/sensors` and `PUT /api/config/sensors/{sensorId}` to read and update sensor behavior, and it MUST validate manual sensor values by sensor type. The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted.

The `PUT /api/config/sensors/{sensorId}` endpoint SHALL accept only the manual-value fields relevant to the addressed sensor type: `value` for all sensors and `raw_color` for color sensors. It SHALL always return a JSON response containing the updated sensor configuration when the write succeeds.

The `PUT /api/config/sensors/{sensorId}` endpoint MUST reject manual updates with `409 Conflict` while a preset is running. Removed scripted-contract fields such as `mode` and `scripted_values` MUST NOT be accepted as aliases for legacy behavior. If they are present in a request, the service SHALL ignore them and continue processing supported manual-value fields.

Input normalization for manual values (for example string booleans to native booleans and numeric strings to numbers) SHALL be performed before the handler applies the update.

#### Scenario: Sensor behavior is updated while idle
- **WHEN** a client updates a sensor while no preset is running using only manual-value fields valid for that sensor type
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** it returns the updated configuration as JSON without `mode` or `scripted_values`

#### Scenario: Manual update is rejected during a preset run
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` while a preset is running
- **THEN** the service returns `409 Conflict`
- **AND** it leaves the sensor's current runtime value unchanged

#### Scenario: Removed scripted fields are ignored
- **WHEN** a client updates a sensor using removed fields such as `mode` or `scripted_values`
- **THEN** the service ignores those removed fields instead of translating them into legacy behavior
- **AND** it continues to return the current manual sensor configuration without `mode` or `scripted_values`

#### Scenario: PUT always returns JSON regardless of caller headers
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `HX-Request: true` header while no preset is running
- **THEN** the service SHALL return a JSON response with the updated sensor configuration
- **AND** the response content-type SHALL be `application/json`

#### Scenario: String boolean value is normalized
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `value` as `"true"`
- **THEN** the service SHALL normalize the value to boolean `true` before processing
- **AND** the response SHALL contain `value` as a native boolean

## ADDED Requirements

### Requirement: Preset-driven sensor lifecycle
Sensors MUST begin in manual-control state using their configured default values. When a preset starts, preset step `sensorUpdates` MUST become the only runtime source of sensor value changes until the run completes or stops.

During a running preset, sensor reads and sensor-configuration snapshots MUST expose the live preset-applied value, and existing downstream integrations such as MQTT publishing MUST continue to use that live value.

When a preset completes or is stopped, sensors MUST return to manual-control state and MUST retain the last preset-applied value as the current manual value. Reset behavior remains governed by the existing run reset contract.

#### Scenario: Running preset drives live sensor values
- **WHEN** a preset step applies `sensorUpdates` to one or more sensors
- **THEN** subsequent sensor reads return the live preset-applied values
- **AND** runtime integrations such as MQTT publishing observe those same live values

#### Scenario: Completed preset restores manual control with the last value
- **WHEN** a preset finishes after applying one or more sensor updates
- **THEN** the sensors become manually editable again
- **AND** each sensor keeps the last value applied by the preset as its current manual value

#### Scenario: Stopped preset restores manual control with the current value
- **WHEN** an operator stops a running preset after one or more sensor updates have already been applied
- **THEN** the sensors become manually editable again
- **AND** each sensor keeps the most recent preset-applied value until an operator changes it manually