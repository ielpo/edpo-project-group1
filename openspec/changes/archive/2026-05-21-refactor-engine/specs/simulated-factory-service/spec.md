# Simulated Factory Service

Version: v1

## Purpose

Describe the externally visible simulator contract for the explicit factory simulation model used by simulated-factory, including runtime snapshots, request-driven control points, sensor compatibility, and event visibility.

## Requirements

## ADDED Requirements

### Requirement: Coherent factory simulation snapshot
The service MUST expose the current simulation state as one coherent snapshot across runtime status, gate state, pending actions, sensor configuration, and event history. Within a single request-response cycle, the snapshot MUST remain internally consistent and MUST not require callers to infer state by combining unrelated endpoints.

#### Scenario: Client inspects the simulator during a gated step
- **WHEN** a client reads runtime status and pending actions while a preset is waiting on a gate
- **THEN** both responses describe the same run identifier and active gate
- **AND** the client can determine the current factory state without contradictory snapshots

### Requirement: Explicit sensor type selection with backward compatibility
The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted. Built-in sensor behavior MUST remain compatible with the existing fixed and scripted sensor modes, including legacy `scripted_values` input forms where they are already supported.

#### Scenario: Sensor type is declared explicitly
- **WHEN** a sensor is configured with `type: color`
- **THEN** the service uses the color sensor implementation for that sensor
- **AND** the sensor continues to honor the configured mode and value fields

#### Scenario: Existing sensor config without type still works
- **WHEN** an existing configuration defines `color-left` without an explicit `type`
- **THEN** the service infers the sensor type from the sensor id prefix
- **AND** the sensor behavior remains unchanged

## MODIFIED Requirements

### Requirement: Runtime status endpoint
The service MUST provide `GET /api/status` and MUST return a coherent snapshot of the current simulation state, including a run identifier, status, current preset, current step, timestamp, and the active `waitingForRequest` gate when one exists.

#### Scenario: Client reads runtime status during a gated step
- **WHEN** a client requests `GET /api/status` while a preset is waiting on a request gate
- **THEN** the response includes the current run identifier, status, current preset, current step, timestamp, and a `waitingForRequest` object with the gate method and path pattern
- **AND** the snapshot reflects the same run state seen by the rest of the service

### Requirement: Run control endpoints
The service MUST provide `POST /api/presets/run`, `POST /api/presets/stop`, and `POST /api/presets/reset` to control the current simulation run, and stop/reset MUST clear any active gate state before returning.

#### Scenario: Stop clears the active gate
- **WHEN** a client requests `POST /api/presets/stop` while the engine is waiting on a gated step
- **THEN** the active gate is cleared
- **AND** the simulation reports that it is stopping or stopped

#### Scenario: Reset clears the active gate and pending run state
- **WHEN** a client requests `POST /api/presets/reset`
- **THEN** the active gate is cleared
- **AND** the runtime state returns to the initial idle state

### Requirement: Preset catalog and deterministic execution
The service MUST load named presets from `presets.yml`, MUST expose the available preset names, and MUST execute a requested preset deterministically. Steps without `awaitRequest` advance after `delayMs` milliseconds. Steps with `awaitRequest` hold until a matching incoming HTTP request is received or `delayMs` milliseconds elapse as a timeout, whichever comes first. When a gate fires, the updated simulation state MUST be visible before the triggering request completes.

#### Scenario: Preset with gated steps waits for requests
- **WHEN** a client requests `POST /api/presets/run` with a preset that has steps declaring `awaitRequest`
- **THEN** the service starts the preset
- **AND** gated steps hold until a matching incoming request arrives or `delayMs` elapses
- **AND** a request that fires the gate observes the updated sensor and state snapshot

### Requirement: Sensor configuration management
The service MUST provide `GET /api/config/sensors` and `PUT /api/config/sensors/{sensorId}` to read and update sensor behavior, and it MUST validate sensor modes and values. Valid sensor modes are `fixed` and `scripted` only. The service MUST continue to support the existing `scripted_values` list behavior, and it MUST preserve prefix-based sensor inference for existing configs that do not specify `type`.

#### Scenario: Sensor behavior is updated with explicit type
- **WHEN** a client updates a sensor configuration that includes `type: ir`
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** subsequent reads use the IR sensor implementation and return the updated configuration with `mode: fixed` or `mode: scripted` as appropriate

#### Scenario: Unknown mode is rejected
- **WHEN** a client updates a sensor with an unrecognized mode value
- **THEN** the service MUST NOT apply the update silently
- **AND** it returns an error or ignores the unknown mode field
