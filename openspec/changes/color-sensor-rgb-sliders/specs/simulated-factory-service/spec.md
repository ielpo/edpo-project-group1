## MODIFIED Requirements

### Requirement: Sensor configuration management
The service MUST provide `GET /api/config/sensors` and `PUT /api/config/sensors/{sensorId}` to read and update sensor behavior, and it MUST validate manual sensor values by sensor type. The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted.

The `PUT /api/config/sensors/{sensorId}` endpoint SHALL accept only the manual-value fields relevant to the addressed sensor type: `value` for all sensors and `raw_color` for color sensors. For color sensors, `raw_color` SHALL be a three-element RGB array with integer channel values in the inclusive range `0-255`. For distance sensors, `value` SHALL be a floating-point number in the inclusive range `0.0-30.0`. The endpoint SHALL always return a JSON response containing the updated sensor configuration when the write succeeds.

For color sensors, a request that provides only a named `value` SHALL be normalized to the canonical RGB mapping for that color before the update is applied. A request that provides `raw_color` SHALL persist that RGB triple as the committed value, and the service SHALL derive the effective named color only by exact canonical RGB match.

For distance sensors, a request that provides `value` SHALL persist that floating-point number only when it lies within the inclusive range `0.0-30.0`. The service MUST reject out-of-range distance values instead of silently clamping them.

The `PUT /api/config/sensors/{sensorId}` endpoint MUST reject manual updates with `409 Conflict` while a preset is running. Removed scripted-contract fields such as `mode` and `scripted_values` MUST NOT be accepted as aliases for legacy behavior. If they are present in a request, the service SHALL ignore them and continue processing supported manual-value fields.

Input normalization for manual values (for example string booleans to native booleans, numeric strings to numbers, and RGB list coercion for color sensors) SHALL be performed before the handler applies the update.

#### Scenario: Sensor behavior is updated while idle
- **WHEN** a client updates a sensor while no preset is running using only manual-value fields valid for that sensor type
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** it returns the updated configuration as JSON without `mode` or `scripted_values`

#### Scenario: Named color update writes canonical RGB
- **WHEN** a client sends `PUT /api/config/sensors/color-left` with `{ "value": "GREEN" }` while idle
- **THEN** the service persists `raw_color` as `[0, 255, 0]`
- **AND** it returns the updated configuration with the canonical RGB triple

#### Scenario: Manual RGB update remains unnamed when non-canonical
- **WHEN** a client sends `PUT /api/config/sensors/color-left` with a non-canonical RGB triple such as `[12, 34, 56]`
- **THEN** the service persists that exact RGB triple
- **AND** the committed color sensor state does not claim a named color unless the triple exactly matches a canonical preset

#### Scenario: Distance update stores in-range float value
- **WHEN** a client sends `PUT /api/config/sensors/distance-left` with `{ "value": 12.5 }` while idle
- **THEN** the service persists `12.5` as the committed distance value
- **AND** it returns the updated configuration as JSON

#### Scenario: Distance update rejects out-of-range value
- **WHEN** a client sends `PUT /api/config/sensors/distance-left` with `{ "value": 31.0 }`
- **THEN** the service rejects the request because the value is outside the supported `0.0-30.0` range
- **AND** it leaves the committed distance sensor state unchanged

#### Scenario: Manual update is rejected during a preset run
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` while a preset is running
- **THEN** the service returns `409 Conflict`
- **AND** it leaves the sensor's current runtime value unchanged

#### Scenario: Removed scripted fields are ignored
- **WHEN** a client updates a sensor using removed fields such as `mode` or `scripted_values`
- **THEN** the service ignores those removed fields instead of translating them into legacy behavior
- **AND** it continues to return the current manual sensor configuration without `mode` or `scripted_values`

#### Scenario: PUT always returns JSON regardless of caller headers
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `HX-Request: true` header
- **THEN** the service SHALL return a JSON response with the updated sensor configuration
- **AND** the response content-type SHALL be `application/json`

#### Scenario: String boolean value is normalized
- **WHEN** a client sends `PUT /api/config/sensors/{sensorId}` with `value` as `"true"`
- **THEN** the service SHALL normalize the value to boolean `true` before processing
- **AND** the response SHALL contain `value` as a native boolean

### Requirement: Color sensor compatibility
The service MUST expose a color-reading response that returns the configured color and raw color vector in the same shape used by the existing color sensor service or its documented simulator equivalent.

For simulator-managed color sensors, the `raw_color` vector SHALL be represented as three RGB channel values in the inclusive range `0-255`.

The canonical named-color mappings SHALL be:
- `RED` -> `[255, 0, 0]`
- `GREEN` -> `[0, 255, 0]`
- `BLUE` -> `[0, 0, 255]`
- `YELLOW` -> `[255, 255, 0]`

#### Scenario: Color read matches configured sensor
- **WHEN** a client reads color from the simulator
- **THEN** the service returns a color value and raw color vector that compatible clients can consume without code changes

#### Scenario: Color read returns byte-style RGB values
- **WHEN** a color sensor is configured with a manual RGB triple
- **THEN** the service returns `raw_color` as the committed three-channel `0-255` RGB vector
- **AND** clients do not need to infer byte values from boolean-like channels

## ADDED Requirements

### Requirement: Slider sensor preview endpoint
The service MUST expose a non-persistent preview endpoint for color and distance sensor controls that accepts draft form values and returns the rendered HTML fragment for the addressed slider-based sensor control.

The preview endpoint SHALL apply the same normalization and validation rules used by `PUT /api/config/sensors/{sensorId}` for color and distance sensors, but it SHALL NOT mutate committed runtime sensor state.

#### Scenario: Preview request normalizes a named color draft
- **WHEN** a client submits a preview request for `color-left` with `value` set to `BLUE`
- **THEN** the response returns a color-sensor HTML fragment with RGB slider values `[0, 0, 255]`
- **AND** the simulator's committed `color-left` configuration remains unchanged

#### Scenario: Preview request normalizes a manual RGB draft
- **WHEN** a client submits a preview request for `color-left` with `raw_color` set to `[255, 200, 0]`
- **THEN** the response returns a color-sensor HTML fragment whose sliders reflect `[255, 200, 0]`
- **AND** the named-color selector renders `(none)` because the RGB triple is non-canonical
- **AND** the simulator's committed `color-left` configuration remains unchanged

#### Scenario: Preview request normalizes an in-range distance draft
- **WHEN** a client submits a preview request for `distance-left` with `value` set to `12.5`
- **THEN** the response returns a distance-sensor HTML fragment whose slider reflects `12.5`
- **AND** the simulator's committed `distance-left` configuration remains unchanged