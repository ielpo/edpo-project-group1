# Simulated Factory Service

Version: v1

## Purpose

Describe the externally visible simulator contract for the simulated-factory service, including HTTP, WebSocket, sensor, event history, and bridge behavior.
## Requirements
### Requirement: Coherent factory simulation snapshot
The service MUST expose the current simulation state as one coherent snapshot across runtime status, gate state, pending actions, sensor configuration, and event history. Within a single request-response cycle, the snapshot MUST remain internally consistent and MUST not require callers to infer state by combining unrelated endpoints.

#### Scenario: Client inspects the simulator during a gated step
- **WHEN** a client reads runtime status and pending actions while a preset is waiting on a gate
- **THEN** both responses describe the same run identifier and active gate
- **AND** the client can determine the current factory state without contradictory snapshots

### Requirement: Explicit sensor type selection with backward compatibility
The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted. Built-in sensor behavior MUST remain compatible with the existing `fixed` and `scripted` sensor modes, including legacy `scripted_values` input forms where they are already supported.

#### Scenario: Sensor type is declared explicitly
- **WHEN** a sensor is configured with `type: color`
- **THEN** the service uses the color sensor implementation for that sensor
- **AND** the sensor continues to honor the configured mode and value fields

#### Scenario: Existing sensor config without type still works
- **WHEN** an existing configuration defines `color-left` without an explicit `type`
- **THEN** the service infers the sensor type from the sensor id prefix
- **AND** the sensor behavior remains unchanged

### Requirement: Versioned simulator contract
The simulator service MUST expose its developer-facing HTTP and WebSocket contract under the `/api` base path and MUST publish `v1` as the current contract version.

#### Scenario: Client uses the documented API version
- **WHEN** a client requests a documented simulator endpoint such as `GET /api/status`
- **THEN** the service responds with the v1 payload shape described by this spec
- **AND** the contract version is discoverable as `v1`

### Requirement: Health endpoint
The service MUST provide `GET /health` and MUST return `200 OK` when the service is ready to accept requests.

#### Scenario: Readiness probe succeeds
- **WHEN** a readiness probe requests `GET /health`
- **THEN** the service returns `200 OK`
- **AND** the response indicates the service is ready

### Requirement: Runtime status endpoint
The service MUST provide `GET /api/status` and MUST return a coherent snapshot of the current simulation state, including a run identifier, status, current preset, current step, timestamp, and the active `waitingForRequest` gate when one exists.

#### Scenario: Client reads runtime status during a gated step
- **WHEN** a client requests `GET /api/status` while a preset is waiting on a request gate
- **THEN** the response includes the current run identifier, status, current preset, current step, timestamp, and a `waitingForRequest` object with the gate method and path pattern
- **AND** the snapshot reflects the same run state seen by the rest of the service

### Requirement: Preset catalog and deterministic execution
The service MUST load named presets from `presets.yml`, MUST expose the available preset names, and MUST execute a requested preset deterministically. Steps without `awaitRequest` advance after `delayMs` milliseconds. Steps with `awaitRequest` hold until a matching incoming HTTP request is received or `delayMs` milliseconds elapse as a timeout, whichever comes first. When a gate fires, the updated simulation state MUST be visible before the triggering request completes.

#### Scenario: Happy-path preset runs reproducibly (non-gated steps)
- **WHEN** a client requests `POST /api/presets/run` with `{ "preset": "happy-path" }`
- **AND** no steps in that preset declare `awaitRequest`
- **THEN** the service accepts the run request
- **AND** it starts the named preset advancing each step after `delayMs`
- **AND** repeating the same preset with the same configuration yields the same sequence of simulation outcomes

#### Scenario: Preset with gated steps waits for requests
- **WHEN** a client requests `POST /api/presets/run` with a preset that has steps declaring `awaitRequest`
- **THEN** the service starts the preset
- **AND** gated steps hold until a matching incoming request arrives or `delayMs` elapses
- **AND** a request that fires the gate observes the updated sensor and state snapshot

#### Scenario: Preset list includes configured names
- **WHEN** a client requests `GET /api/presets`
- **THEN** the service returns the configured preset names, including presets loaded from `presets.yml`

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

### Requirement: Event history and live status stream
The service MUST record an in-memory chronological event history and MUST expose it through `GET /api/events` with paging and filtering. It MUST stream state diffs and key events over WebSocket `/ws/status`.

The service MUST support an explicit process-focused filter mode in addition to full history mode. Process-focused mode MUST include only process-relevant event types (`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`) while full mode retains all event types (including `REST`, `STATE`, and `MQTT`).

The service MUST continue recording all events in complete history regardless of selected filter mode.

#### Scenario: Events can be queried in full mode
- **WHEN** a client requests `GET /api/events?page=1&pageSize=50`
- **THEN** the service returns events in chronological order including all recorded event categories
- **AND** it returns the next page token or page number when more results exist

#### Scenario: Process-focused events can be queried
- **WHEN** a client requests `GET /api/events?page=1&pageSize=50&filter=process`
- **THEN** the service returns only process-relevant event types (`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`)
- **AND** events of types such as `REST`, `STATE`, and `MQTT` are excluded from this filtered result

#### Scenario: UI receives a live update
- **WHEN** the simulation state changes
- **THEN** connected clients on `/ws/status` receive a JSON state diff or snapshot

### Requirement: Dobot simulation contract
The service MUST accept simulated Dobot commands at `POST /api/dobot/{name}/commands` and MUST expose `GET /api/dobot/{name}/color`, `GET /api/dobot/{name}/ir`, and `GET /api/dobot/{name}/state` with payloads compatible with `dobot-control`.

When interactive mode is active and the incoming command batch contains at least one command type in the intercepted set, the service MUST suspend the response and queue a `PendingAction` rather than resolving immediately. The response is completed (with `202 Accepted`) once the operator resolves the action or the configured timeout expires.

The response body for `POST /api/dobot/{name}/commands` SHALL include:
- `correlationId`: string identifier for the command batch (always present)
- `outcome`: `"success"` or `"failure"` (present only when interactive mode resolved the action; omitted in non-interactive path to preserve backward compatibility)
- `timedOut`: `true` (present only when the action expired; omitted otherwise)

Inbound sensor reads for simulated Dobot color/IR endpoints MUST be tagged as `SENSOR_REQUEST` events in the local event history.

#### Scenario: Dobot command is accepted asynchronously (non-interactive)
- **WHEN** a client sends one or more movement, suction, or conveyor commands to `POST /api/dobot/{name}/commands`
- **AND** none of the command types are in the intercepted set
- **THEN** the service returns `202 Accepted` with a correlation identifier
- **AND** it does not block until the command completes

#### Scenario: Dobot command is intercepted and held (interactive)
- **WHEN** a client sends a command to `POST /api/dobot/{name}/commands`
- **AND** the command type is in the configured intercepted set
- **THEN** the service queues a `PendingAction` and suspends the response
- **AND** the response is not completed until the operator resolves the action or the timeout fires

#### Scenario: Sensor reads return simulated values
- **WHEN** a client requests color or IR state for a simulated Dobot
- **THEN** the service returns the configured or scenario-driven value in the documented response shape

#### Scenario: Sensor read emits SENSOR_REQUEST event
- **WHEN** a client requests `GET /api/dobot/{name}/color` or `GET /api/dobot/{name}/ir`
- **THEN** the service records a `SENSOR_REQUEST` event including endpoint and method metadata
- **AND** the event is eligible for the process-focused filter

### Requirement: Color sensor compatibility
The service MUST expose a color-reading response that returns the configured color and raw color vector in the same shape used by the existing color sensor service or its documented simulator equivalent.

#### Scenario: Color read matches configured sensor
- **WHEN** a client reads color from the simulator
- **THEN** the service returns a color value and raw color vector that compatible clients can consume without code changes

### Requirement: Distance sensor MQTT publishing
The service MUST publish Tinkerforge-compatible distance messages to a configurable MQTT broker and topic using the `distance_IR_short` JSON shape, with deterministically incrementing `messageID` during a run.

#### Scenario: Distance reading is published
- **WHEN** a preset enables the distance sensor publisher
- **THEN** the service publishes a JSON payload containing `type`, `UID`, `location`, `messageID`, and `distance` on the configured topic
- **AND** the `messageID` advances deterministically for the run

### Requirement: Event bridge modes
The service MUST support `SIMULATOR_EVENT_BRIDGE` values `kafka`, `http`, and `none`, and MUST route simulator-origin events according to the selected mode. Bridge delivery MUST be scheduled asynchronously so slow external callbacks do not block simulation state progression.

#### Scenario: HTTP bridge is enabled
- **WHEN** `SIMULATOR_EVENT_BRIDGE=http`
- **AND** the configured HTTP callback target responds slowly
- **THEN** simulator-origin events are still queued for delivery asynchronously
- **AND** the simulation loop continues advancing state
- **AND** the same event remains in the local event history

### Requirement: Kafka process-event observer
The simulated-factory service MUST run a Kafka consumer in observer mode that subscribes to process topics and appends consumed messages to local event history as `KAFKA` events.

The consumer MUST use consumer group id `simulated-factory` and MUST default to bootstrap server `localhost:9092`.

The observer MUST subscribe to:
- `order.manufacture.v1`
- `order.complete.v1`
- `info.v1`
- `error.v1`

#### Scenario: Simulated-factory consumes process topics in parallel
- **WHEN** a message is published to `order.manufacture.v1`
- **THEN** factory-service continues normal consumption behavior
- **AND** simulated-factory also consumes the message independently through group `simulated-factory`
- **AND** simulated-factory appends a `KAFKA` event containing topic and payload details

#### Scenario: Kafka connection unavailable
- **WHEN** simulated-factory cannot connect to `localhost:9092`
- **THEN** the service remains available for HTTP simulation endpoints
- **AND** it logs consumer connection failure
- **AND** no synthetic process events are emitted for missing Kafka messages

