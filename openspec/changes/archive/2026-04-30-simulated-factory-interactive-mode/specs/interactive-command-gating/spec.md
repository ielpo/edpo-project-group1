# Interactive Command Gating

Version: v1

## ADDED Requirements

### Requirement: Interactive configuration endpoint
The service SHALL expose `GET /api/interactive/config` and `PUT /api/interactive/config` to read and replace the set of intercepted command types and the action timeout.

#### Scenario: Client reads interactive configuration
- **WHEN** a client requests `GET /api/interactive/config`
- **THEN** the service returns the current set of intercepted command types and the timeout value in seconds

#### Scenario: Client enables interception for move commands
- **WHEN** a client sends `PUT /api/interactive/config` with `{"intercepted": ["move"], "timeoutSeconds": 30}`
- **THEN** the service stores the new configuration
- **AND** subsequent `move` commands to `POST /api/dobot/{name}/commands` are held pending instead of auto-resolved

#### Scenario: Client clears all interceptions
- **WHEN** a client sends `PUT /api/interactive/config` with `{"intercepted": [], "timeoutSeconds": 30}`
- **THEN** no command types are intercepted and all commands resolve immediately as before

### Requirement: Pending action queue
The service SHALL maintain an in-memory queue of pending actions and expose it at `GET /api/interactive/pending`. Each pending action SHALL include a unique identifier, the robot name, the list of command payloads, and the time the action was created.

#### Scenario: Client lists pending actions
- **WHEN** one or more commands matching an intercepted type are received
- **AND** a client requests `GET /api/interactive/pending`
- **THEN** the response lists each unresolved pending action with its identifier, robot name, commands, and creation timestamp

#### Scenario: No pending actions
- **WHEN** no commands are waiting for resolution
- **AND** a client requests `GET /api/interactive/pending`
- **THEN** the response returns an empty list

### Requirement: Action resolution endpoint
The service SHALL expose `POST /api/interactive/{actionId}/resolve` accepting `{"outcome": "success" | "failure", "reason": "<optional string>"}` to resolve a pending action. Resolving an action SHALL unblock the suspended command response and return the chosen outcome to the original caller.

#### Scenario: Operator approves a pending action
- **WHEN** an operator sends `POST /api/interactive/{actionId}/resolve` with `{"outcome": "success"}`
- **THEN** the suspended `POST /api/dobot/{name}/commands` response returns `202` with `{"correlationId": "...", "outcome": "success"}`
- **AND** the action is removed from the pending queue

#### Scenario: Operator rejects a pending action
- **WHEN** an operator sends `POST /api/interactive/{actionId}/resolve` with `{"outcome": "failure"}`
- **THEN** the suspended `POST /api/dobot/{name}/commands` response returns `202` with `{"correlationId": "...", "outcome": "failure"}`
- **AND** the action is removed from the pending queue

#### Scenario: Resolving an unknown action
- **WHEN** a client sends `POST /api/interactive/{actionId}/resolve` with an action identifier that does not exist
- **THEN** the service returns `404 Not Found`

### Requirement: Automatic timeout and failure
The service SHALL automatically resolve pending actions as failures after the configured timeout has elapsed. Timed-out actions SHALL be removed from the pending queue and SHALL cause the suspended command response to return with `{"outcome": "failure", "timedOut": true}`.

#### Scenario: Action times out before operator resolves it
- **WHEN** a pending action is not resolved within the configured `timeoutSeconds`
- **THEN** the service automatically resolves it as failure
- **AND** the suspended command response returns `202` with `{"correlationId": "...", "outcome": "failure", "timedOut": true}`
- **AND** the action no longer appears in the pending queue

### Requirement: Event store integration for pending actions
The service SHALL record a `PENDING_ACTION` event when an action is queued and an `ACTION_RESOLVED` event when it is resolved or timed out. Both events SHALL be broadcast to WebSocket and SSE subscribers.

#### Scenario: Pending action events appear in event history
- **WHEN** a command is intercepted and later resolved
- **THEN** `GET /api/events` returns a `PENDING_ACTION` entry followed by an `ACTION_RESOLVED` entry for that action
