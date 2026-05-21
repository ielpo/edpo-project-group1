# Simulated Factory Service

Version: v1

## Requirements

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
The service MUST provide `GET /api/status` and MUST return the current simulation state, including a run identifier, status, current preset, current step, and timestamp.

#### Scenario: Client reads runtime status
- **WHEN** a client requests `GET /api/status`
- **THEN** the response includes the current run identifier, status, current preset, current step, and timestamp

### Requirement: Preset catalog and deterministic execution
The service MUST load named presets from `presets.yml`, MUST expose the available preset names, and MUST execute a requested preset deterministically. Steps without `awaitRequest` advance after `delayMs` milliseconds. Steps with `awaitRequest` advance when a matching incoming HTTP request is received or `delayMs` milliseconds elapse as a timeout — whichever comes first.

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
- **AND** repeating the run with the same request sequence yields the same outcome

#### Scenario: Preset list includes configured names
- **WHEN** a client requests `GET /api/presets`
- **THEN** the service returns the configured preset names, including presets loaded from `presets.yml`

### Requirement: Run control endpoints
The service MUST provide `POST /api/presets/run`, `POST /api/presets/stop`, and `POST /api/presets/reset` to control the current simulation run.

#### Scenario: Active run is stopped
- **WHEN** a client requests `POST /api/presets/stop`
- **THEN** the service stops the active run and reports that the simulation is stopping or stopped

#### Scenario: State is reset
- **WHEN** a client requests `POST /api/presets/reset`
- **THEN** the service resets the runtime state to the initial idle state

### Requirement: Sensor configuration management
The service MUST provide `GET /api/config/sensors` and `PUT /api/config/sensors/{sensorId}` to read and update sensor behavior, and it MUST validate sensor modes and values.

#### Scenario: Sensor behavior is updated
- **WHEN** a client updates a sensor with a valid mode such as `fixed`, `random`, or `scripted`
- **AND** the submitted values satisfy validation rules such as the `failRate` range
- **THEN** the service stores the updated sensor configuration in runtime memory
- **AND** it returns the updated configuration

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
The service MUST support `SIMULATOR_EVENT_BRIDGE` values `kafka`, `http`, and `none`, and MUST route simulator-origin events according to the selected mode.

#### Scenario: HTTP bridge is enabled
- **WHEN** `SIMULATOR_EVENT_BRIDGE=http`
- **THEN** simulator-origin events are delivered to the configured HTTP callback target
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
