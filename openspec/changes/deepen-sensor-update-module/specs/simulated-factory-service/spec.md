## MODIFIED Requirements

### Requirement: Sensor configuration management
The service MUST provide `GET /api/config/sensors` and `PUT /api/config/sensors/{sensorId}` to read and update sensor behavior, and it MUST validate sensor modes and values. The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted. Built-in sensor behavior MUST remain compatible with the existing `fixed` and `scripted` modes, and legacy `scripted_values` input forms MUST continue to be supported.

The `PUT /api/config/sensors/{sensorId}` endpoint SHALL accept either an array for `scripted_values` or a legacy CSV string; the server supports both for backward compatibility. Unknown or invalid modes MUST be rejected.

The `PUT /api/config/sensors/{sensorId}` endpoint SHALL always return a JSON response containing the updated sensor configuration, regardless of request headers. Input normalization (CSV strings to lists, string booleans to native booleans, numeric strings to numbers) SHALL be performed by model-level validators before the handler executes.

Valid sensor modes are `fixed` and `scripted` only. The `random` mode and the `failRate` field are removed from the API contract.

- `fixed`: the sensor always returns `value`.
- `scripted`: the sensor returns `scripted_values[currentStep - 1]` (clamped to bounds). If `scripted_values` is empty, behavior falls back to `value`.

#### Scenario: Sensor behavior is updated with explicit type
- **WHEN** a client updates a sensor configuration that includes `type: ir`
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** subsequent reads use the IR sensor implementation and return the updated configuration with `mode: fixed` or `mode: scripted` as appropriate

#### Scenario: Sensor behavior is updated with fixed mode
- **WHEN** a client updates a sensor with `mode: fixed` and a `value`
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** it returns the updated configuration as JSON with `mode: fixed`

#### Scenario: Sensor behavior is updated with scripted mode
- **WHEN** a client updates a sensor with `mode: scripted` and a non-empty `scripted_values` list
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** subsequent reads return `scripted_values[currentStep - 1]` during a running preset

#### Scenario: Unknown mode is rejected
- **WHEN** a client updates a sensor with an unrecognized mode value
- **THEN** the service MUST NOT apply the update silently
- **AND** it returns an error or ignores the unknown mode field

#### Scenario: PUT always returns JSON regardless of caller headers
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `HX-Request: true` header
- **THEN** the service SHALL return a JSON response with the updated sensor configuration
- **AND** the response content-type SHALL be `application/json`

#### Scenario: CSV string input is normalized to a list
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `raw_color` as `"0,128,255"`
- **THEN** the service SHALL normalize the value to `[0, 128, 255]` before processing
- **AND** the response SHALL contain `raw_color` as a list of integers

#### Scenario: String boolean value is normalized
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `value` as `"true"`
- **THEN** the service SHALL normalize the value to boolean `true` before processing
- **AND** the response SHALL contain `value` as a native boolean
