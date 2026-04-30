# Request-Gated Preset Steps

Version: v1

## Requirements

### Requirement: Gated step declaration in preset YAML
A preset step SHALL support an optional `awaitRequest` field. When present, the step SHALL NOT advance after `delayMs` has elapsed as a simple sleep; instead it SHALL hold until a matching incoming HTTP request is received or the `delayMs` timeout expires.

The `awaitRequest` field SHALL be an object with two sub-fields:
- `method`: HTTP method string (e.g., `POST`, `GET`)
- `path`: URL path pattern using `{name}` wildcards (e.g., `/api/dobot/{name}/commands`)

Steps without `awaitRequest` SHALL continue to use `delayMs` as a simple sleep, with no change to existing behaviour.

#### Scenario: Step without awaitRequest advances on timer
- **WHEN** a preset step has no `awaitRequest` field
- **THEN** the engine SHALL sleep for `delayMs` milliseconds and then advance to the next step
- **AND** sensor updates and distance publications for that step SHALL be applied before the sleep, as today

#### Scenario: Step with awaitRequest holds until matching request arrives
- **WHEN** a preset step declares `awaitRequest: {method: POST, path: /api/dobot/{name}/commands}`
- **AND** the engine reaches that step
- **THEN** the engine SHALL hold at that step without advancing
- **AND** it SHALL NOT apply sensor updates or distance publications yet

#### Scenario: Matching request fires the gate
- **WHEN** the engine is holding at a gated step
- **AND** an incoming HTTP request matches the declared method and path pattern
- **THEN** the engine SHALL apply the step's `sensorUpdates` and `publishDistance` at that moment
- **AND** it SHALL advance to the next step
- **AND** the request that fired the gate SHALL observe the updated sensor state

#### Scenario: Gate timeout expires before matching request
- **WHEN** the engine is holding at a gated step
- **AND** no matching request arrives within `delayMs` milliseconds
- **THEN** the engine SHALL emit a `STATE` event with `{"gateTimedOut": true}` in the payload
- **AND** it SHALL apply the step's `sensorUpdates` and `publishDistance`
- **AND** it SHALL advance to the next step

#### Scenario: Stop clears the active gate
- **WHEN** `POST /api/presets/stop` or `POST /api/presets/reset` is called while the engine is holding at a gated step
- **THEN** the gate SHALL be cleared immediately
- **AND** the preset SHALL terminate without advancing further

### Requirement: Gate side-effects applied atomically on gate fire
When a gated step's gate fires (either by a matching request or timeout), the engine SHALL apply `sensorUpdates` and call `publishDistance` before signalling the asyncio event that unblocks the preset loop.

This ensures that the HTTP request handler that triggered the gate (or the timeout path) sees an already-updated sensor state on any subsequent sensor read within the same request.

#### Scenario: Sensor state visible to triggering request
- **WHEN** a request fires a gate on a step with `sensorUpdates`
- **AND** the same request subsequently reads a sensor (e.g., `GET /api/dobot/{name}/color`)
- **THEN** the sensor SHALL return the value set by the gate step's `sensorUpdates`

### Requirement: Gate status exposed in simulation state
While the engine is holding at a gated step, the `GET /api/status` response SHALL include a `waitingForRequest` field with the `method` and `path` pattern of the active gate. When no gate is active the field SHALL be absent or `null`.

#### Scenario: Status reflects active gate
- **WHEN** the engine is holding at a gated step
- **AND** a client requests `GET /api/status`
- **THEN** the response SHALL include `waitingForRequest: {method: "POST", path: "/api/dobot/{name}/commands"}`

#### Scenario: Status has no gate when idle
- **WHEN** no preset is running or no step has an active gate
- **AND** a client requests `GET /api/status`
- **THEN** `waitingForRequest` SHALL be absent or `null`
