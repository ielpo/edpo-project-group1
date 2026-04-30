## MODIFIED Requirements

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

## ADDED Requirements

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
