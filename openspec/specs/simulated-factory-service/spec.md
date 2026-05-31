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
The service MUST support an explicit `type` field for sensor entries in `config.yml` and MUST continue to infer sensor types from sensor id prefixes when `type` is omitted. Built-in sensor defaults MUST store only the current manual value and sensor-specific static metadata; `mode` and `scripted_values` MUST NOT be part of the sensor default contract.

#### Scenario: Sensor type is declared explicitly
- **WHEN** a sensor is configured with `type: color`
- **THEN** the service uses the color sensor implementation for that sensor
- **AND** the sensor default stores its manual `value`, optional `raw_color`, and static metadata without a configured mode field

#### Scenario: Existing sensor config without type still works
- **WHEN** an existing configuration defines `color-left` without an explicit `type`
- **THEN** the service infers the sensor type from the sensor id prefix
- **AND** the sensor default remains usable without legacy `mode` or `scripted_values` fields

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

