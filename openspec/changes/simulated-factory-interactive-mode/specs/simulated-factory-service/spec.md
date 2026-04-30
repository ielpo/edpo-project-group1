# Simulated Factory Service — Interactive Mode Delta

Version: v1-delta (interactive-mode)

## MODIFIED Requirements

### Requirement: Dobot simulation contract
The service MUST accept simulated Dobot commands at `POST /api/dobot/{name}/commands` and MUST expose `GET /api/dobot/{name}/color`, `GET /api/dobot/{name}/ir`, and `GET /api/dobot/{name}/state` with payloads compatible with `dobot-control`.

When interactive mode is active and the incoming command batch contains at least one command type in the intercepted set, the service MUST suspend the response and queue a `PendingAction` rather than resolving immediately. The response is completed (with `202 Accepted`) once the operator resolves the action or the configured timeout expires.

The response body for `POST /api/dobot/{name}/commands` SHALL include:
- `correlationId`: string identifier for the command batch (always present)
- `outcome`: `"success"` or `"failure"` (present only when interactive mode resolved the action; omitted in non-interactive path to preserve backward compatibility)
- `timedOut`: `true` (present only when the action expired; omitted otherwise)

#### Scenario: Dobot command is accepted asynchronously (non-interactive)
- **WHEN** a client sends one or more commands to `POST /api/dobot/{name}/commands`
- **AND** none of the command types are in the intercepted set
- **THEN** the service returns `202 Accepted` with a correlation identifier immediately
- **AND** it does not block until the command completes

#### Scenario: Dobot command is intercepted and held (interactive)
- **WHEN** a client sends a command to `POST /api/dobot/{name}/commands`
- **AND** the command type is in the configured intercepted set
- **THEN** the service queues a `PendingAction` and suspends the response
- **AND** the response is not completed until the operator resolves the action or the timeout fires

#### Scenario: Sensor reads return simulated values
- **WHEN** a client requests color or IR state for a simulated Dobot
- **THEN** the service returns the configured or scenario-driven value in the documented response shape
