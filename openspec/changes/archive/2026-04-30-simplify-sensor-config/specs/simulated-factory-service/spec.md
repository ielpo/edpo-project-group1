## MODIFIED Requirements

### Requirement: Sensor configuration management
The service MUST provide `GET /api/config/sensors` and `PUT /api/config/sensors/{sensorId}` to read and update sensor behavior, and it MUST validate sensor modes and values.

Valid sensor modes are `fixed` and `scripted` only. The `random` mode and the `failRate` field are removed from the API contract.

- `fixed`: the sensor always returns `value`.
- `scripted`: the sensor returns `scripted_values[currentStep - 1]` (clamped to bounds). If `scripted_values` is empty, behavior falls back to `value`.

#### Scenario: Sensor behavior is updated with fixed mode
- **WHEN** a client updates a sensor with `mode: fixed` and a `value`
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** it returns the updated configuration with `mode: fixed`

#### Scenario: Sensor behavior is updated with scripted mode
- **WHEN** a client updates a sensor with `mode: scripted` and a non-empty `scripted_values` list
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** subsequent reads return `scripted_values[currentStep - 1]` during a running preset

#### Scenario: Unknown mode is rejected
- **WHEN** a client updates a sensor with an unrecognized mode value
- **THEN** the service MUST NOT apply the update silently; it returns an error or ignores the unknown mode field

## REMOVED Requirements

### Requirement: random sensor mode
**Reason**: The `random` mode was pseudo-deterministic (derived from `sensorId` and preset name) and had no use case in the preset-driven simulation concept.
**Migration**: Replace `mode: random` with `mode: fixed` and an explicit `value`, or use `mode: scripted` with a `scripted_values` list to vary output per step.

### Requirement: failRate sensor field
**Reason**: The `failRate` field was declared in `SensorConfig` but never read by the engine. It implied a probabilistic failure contract that did not exist.
**Migration**: Remove `failRate` from any sensor update payloads. No behavioral replacement is needed.
