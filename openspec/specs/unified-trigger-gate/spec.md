# Unified Trigger Gate

Version: v1

## ADDED Requirements

### Requirement: awaitTrigger step declaration
A preset step SHALL support an optional `awaitTrigger` field containing a trigger type discriminator and type-specific configuration. When present, the step SHALL hold until the declared trigger fires or the timeout elapses.

The `awaitTrigger` field SHALL be an object with:
- `type`: one of `http`, `kafka`, `manual` (required)
- `timeoutMs`: integer, milliseconds before timeout (required)
- `method`: HTTP method string (required when type is `http`)
- `path`: URL path pattern with `{name}` wildcards (required when type is `http`)
- `topic`: Kafka topic name (required when type is `kafka`)

#### Scenario: HTTP gate holds until matching request
- **WHEN** a preset step declares `awaitTrigger: {type: http, method: POST, path: /api/dobot/{name}/commands, timeoutMs: 30000}`
- **AND** the engine reaches that step
- **THEN** the engine SHALL hold at that step without advancing
- **AND** it SHALL wait for a matching HTTP request or timeout

#### Scenario: Kafka gate holds until message on topic
- **WHEN** a preset step declares `awaitTrigger: {type: kafka, topic: order.manufacture.v1, timeoutMs: 30000}`
- **AND** the engine reaches that step
- **THEN** the engine SHALL hold at that step without advancing
- **AND** it SHALL wait for any message on the declared topic or timeout

#### Scenario: Manual gate holds until user action
- **WHEN** a preset step declares `awaitTrigger: {type: manual, timeoutMs: 60000}`
- **AND** the engine reaches that step
- **THEN** the engine SHALL hold at that step without advancing
- **AND** it SHALL wait for a manual fire via `POST /api/gate/fire` or timeout

### Requirement: Mutual exclusivity of delayMs and awaitTrigger
A preset step SHALL have either `delayMs` or `awaitTrigger`, never both. The system SHALL reject preset configurations where both fields are present on the same step.

#### Scenario: Step with both fields is rejected
- **WHEN** a preset step declares both `delayMs: 100` and `awaitTrigger: {type: manual, timeoutMs: 5000}`
- **THEN** the system SHALL raise a validation error at preset load time
- **AND** the preset SHALL NOT start

#### Scenario: Step with only delayMs advances on timer
- **WHEN** a preset step has `delayMs: 100` and no `awaitTrigger`
- **THEN** the engine SHALL sleep for 100 milliseconds and advance to the next step

#### Scenario: Step with only awaitTrigger waits for trigger
- **WHEN** a preset step has `awaitTrigger` and no `delayMs`
- **THEN** the engine SHALL hold until the trigger fires or timeout elapses

### Requirement: Sensor updates apply immediately on gated steps
When the engine reaches a gated step, it SHALL apply `sensorUpdates` immediately before entering the gate wait. The gate is purely a synchronization point; sensor state represents the physical world at that step.

#### Scenario: Sensors updated before gate wait
- **WHEN** the engine reaches a step with `sensorUpdates` and `awaitTrigger`
- **THEN** the sensor values SHALL be updated immediately
- **AND** the engine SHALL then enter the gate wait
- **AND** any sensor read during the wait SHALL return the updated values

### Requirement: Timeout aborts preset
When a gate's `timeoutMs` elapses without the trigger firing, the engine SHALL abort the preset run with an error event. The preset SHALL NOT advance to subsequent steps.

#### Scenario: Gate times out
- **WHEN** the engine is holding at a gated step
- **AND** no matching trigger arrives within `timeoutMs` milliseconds
- **THEN** the engine SHALL emit an error event indicating gate timeout
- **AND** the preset run SHALL terminate
- **AND** no subsequent steps SHALL execute

#### Scenario: Stop during gate wait
- **WHEN** `POST /api/presets/stop` or `POST /api/presets/reset` is called during a gate wait
- **THEN** the gate SHALL be cleared immediately
- **AND** the preset SHALL terminate without advancing further

### Requirement: Single try_fire_gate engine method
The engine SHALL expose a single `try_fire_gate(event: TriggerEvent)` method that accepts a discriminated trigger event. The method SHALL match the event type against the active gate's `awaitTrigger.type` and validate type-specific fields before firing.

#### Scenario: HTTP trigger fires HTTP gate
- **WHEN** the engine has an active gate with `type: http, method: POST, path: /api/dobot/{name}/commands`
- **AND** `try_fire_gate` is called with `TriggerEvent(type="http", method="POST", path="/api/dobot/alpha/commands")`
- **THEN** the gate SHALL fire and the preset SHALL advance

#### Scenario: Kafka trigger fires Kafka gate
- **WHEN** the engine has an active gate with `type: kafka, topic: order.manufacture.v1`
- **AND** `try_fire_gate` is called with `TriggerEvent(type="kafka", topic="order.manufacture.v1")`
- **THEN** the gate SHALL fire and the preset SHALL advance

#### Scenario: Manual trigger fires manual gate
- **WHEN** the engine has an active gate with `type: manual`
- **AND** `try_fire_gate` is called with `TriggerEvent(type="manual")`
- **THEN** the gate SHALL fire and the preset SHALL advance

#### Scenario: Mismatched trigger type does not fire
- **WHEN** the engine has an active gate with `type: http`
- **AND** `try_fire_gate` is called with `TriggerEvent(type="kafka", topic="order.manufacture.v1")`
- **THEN** the gate SHALL NOT fire
- **AND** the method SHALL return without effect

#### Scenario: No active gate
- **WHEN** no gate is currently active
- **AND** `try_fire_gate` is called
- **THEN** the method SHALL return without effect

### Requirement: HTTP gate fires and processes request
When an HTTP request matches an active HTTP gate, the gate SHALL fire as a side-effect and the request SHALL continue to be processed normally by the endpoint handler.

#### Scenario: Request triggers gate and gets processed
- **WHEN** the engine has an active HTTP gate matching `POST /api/dobot/alpha/commands`
- **AND** a client sends `POST /api/dobot/alpha/commands` with command payload
- **THEN** the gate SHALL fire (preset advances)
- **AND** the request SHALL be processed normally by the commands endpoint
- **AND** the client SHALL receive the normal endpoint response

### Requirement: KafkaObserver fires gates
The `KafkaObserver` SHALL be injected with a gate-firing interface. On each consumed message, it SHALL call `try_fire_gate` with a Kafka trigger event containing the message topic.

#### Scenario: Kafka message fires active Kafka gate
- **WHEN** the engine has an active gate with `type: kafka, topic: order.manufacture.v1`
- **AND** a message arrives on topic `order.manufacture.v1`
- **THEN** the `KafkaObserver` SHALL call `try_fire_gate(TriggerEvent(type="kafka", topic="order.manufacture.v1"))`
- **AND** the gate SHALL fire

#### Scenario: Kafka message with no matching gate
- **WHEN** no gate is active or the active gate has a different type/topic
- **AND** a message arrives on a Kafka topic
- **THEN** the `KafkaObserver` SHALL still call `try_fire_gate`
- **AND** the call SHALL return without effect
- **AND** the message SHALL still be recorded as an event (existing behavior)

### Requirement: Manual gate fire endpoint
The service SHALL expose `POST /api/gate/fire` which fires the currently active manual gate. If no manual gate is active, the endpoint SHALL return 404.

#### Scenario: Fire active manual gate
- **WHEN** the engine has an active gate with `type: manual`
- **AND** a client sends `POST /api/gate/fire`
- **THEN** the gate SHALL fire and the preset SHALL advance
- **AND** the endpoint SHALL return `200 OK`

#### Scenario: Reject active manual gate
- **WHEN** the engine has an active gate with `type: manual`
- **AND** a client sends `POST /api/gate/reject`
- **THEN** the gate timeout SHALL be triggered immediately (abort preset)
- **AND** the endpoint SHALL return `200 OK`

#### Scenario: No active manual gate
- **WHEN** no manual gate is currently active
- **AND** a client sends `POST /api/gate/fire`
- **THEN** the endpoint SHALL return `404 Not Found`

### Requirement: PendingAction displays gate state
While a gate is active, the engine SHALL maintain a `PendingAction` with gate metadata: step name, trigger type, trigger specification, timeout, and start time. The UI SHALL render this as a status card showing what the gate is waiting for.

#### Scenario: Manual gate shows approve/reject buttons
- **WHEN** a manual gate is active
- **THEN** the `PendingAction` SHALL have `trigger_type: "manual"`
- **AND** the UI SHALL render approve and reject buttons

#### Scenario: HTTP gate shows waiting details
- **WHEN** an HTTP gate is active
- **THEN** the `PendingAction` SHALL have `trigger_type: "http"` and `trigger_spec` containing method and path
- **AND** the UI SHALL render a read-only status card showing "Waiting for POST /api/dobot/{name}/commands"

#### Scenario: Kafka gate shows waiting details
- **WHEN** a Kafka gate is active
- **THEN** the `PendingAction` SHALL have `trigger_type: "kafka"` and `trigger_spec` containing the topic
- **AND** the UI SHALL render a read-only status card showing "Waiting for message on order.manufacture.v1"

### Requirement: Gate status in simulation state
While the engine is holding at a gated step, `GET /api/status` SHALL include gate information. When no gate is active the field SHALL be absent or null.

#### Scenario: Status reflects active gate
- **WHEN** the engine is holding at a gated step with `awaitTrigger: {type: http, method: POST, path: /api/dobot/{name}/commands, timeoutMs: 30000}`
- **AND** a client requests `GET /api/status`
- **THEN** the response SHALL include gate information with the trigger type and spec

#### Scenario: Status has no gate when idle
- **WHEN** no preset is running or no step has an active gate
- **AND** a client requests `GET /api/status`
- **THEN** gate information SHALL be absent or null
