# Simulated Factory Service API

Version: `v1`

Upgrade notes:

- `v1` is the initial simulator contract.
- Future breaking changes should be introduced under `/v2/...` while keeping `v1` available for `dobot-control` compatibility.

## HTTP API

Base path: `/api`

### GET /api/status

Returns the current simulator state.

Example response:

```json
{
  "id": "run-0000",
  "status": "idle",
  "currentPreset": null,
  "currentStep": 0,
  "currentStepName": null,
  "timestamp": "2026-04-22T12:00:00Z",
  "dobots": {
    "left": {
      "position": {"x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0},
      "speed": 50.0,
      "acceleration": 100.0,
      "suction_enabled": false,
      "conveyor_speed": 0.0,
      "conveyor_distance": 0.0,
      "conveyor_direction": "STOP",
      "last_command": null
    }
  }
}
```

### GET /api/presets

Lists available deterministic presets.

### POST /api/presets/run

Starts a preset asynchronously.

Request:

```json
{
  "preset": "happy-path",
  "speed": "normal"
}
```

Response: `202 Accepted`

```json
{
  "runId": "run-0001",
  "status": "accepted"
}
```

### POST /api/presets/stop

Requests the active run to stop.

### POST /api/presets/reset

Resets runtime state and sensor overrides back to the persisted defaults.

### GET /api/config/sensors

Returns the current sensor configuration.

### PUT /api/config/sensors/{sensorId}

Updates a sensor at runtime.

Example request:

```json
{
  "mode": "fixed",
  "value": "RED",
  "raw_color": [1, 0, 0]
}
```

### GET /api/events

Returns a paged event history. Query parameters:

- `page`: 1-based page number
- `pageSize`: number of items per page
- `filter`: optional substring matched against type, topic, endpoint, method, and message

### POST /api/events

Accepts external events for UI correlation.

### POST /api/dobot/{name}/commands

Accepts a single command or a list of commands and updates the in-memory Dobot state.

Example request:

```json
{
  "type": "move",
  "target": {
    "x": 150.0,
    "y": 20.0,
    "z": 40.0,
    "r": 0.0
  },
  "mode": "MOVE_LINEAR"
}
```

Example response:

```json
{
  "correlationId": "cmd-a1b2c3d4"
}
```

When [interactive mode](#interactive-mode) is active and one or more commands in the
batch match an intercepted command type, this endpoint suspends until an operator
resolves the action through `POST /api/interactive/{actionId}/resolve` or until the
configured timeout elapses. The response then includes the chosen `outcome`:

```json
{
  "correlationId": "cmd-a1b2c3d4",
  "outcome": "success"
}
```

If the action timed out the response also carries `"timedOut": true` and the outcome
is forced to `"failure"`. In non-interactive mode the `outcome` and `timedOut` fields
are omitted to preserve backward compatibility with `dobot-control`.

### GET /api/dobot/{name}/color

Returns the simulated color sensor response used by `DobotFake`.

```json
{
  "color": "RED",
  "raw_color": [1, 0, 0],
  "timestamp": "2026-04-22T12:00:00Z"
}
```

### GET /api/dobot/{name}/ir

Returns the simulated IR sensor state.

```json
{
  "ir": true
}
```

### GET /api/dobot/{name}/state

Returns the current simulated Dobot position, speed, and conveyor state.

### GET /color

Compatibility endpoint matching the existing color sensor service, returning RGB bytes.

```json
{
  "r": 255,
  "g": 0,
  "b": 0
}
```

### GET /health

Returns `200 OK` when the service is ready.

## Interactive Mode

Interactive mode lets an operator gate selected Dobot command types so that the
suspended `POST /api/dobot/{name}/commands` response is completed only after a manual
success/failure decision. It is disabled by default (no command types intercepted) and
the configuration is held in memory only.

### GET /api/interactive/config

Returns the current interactive configuration.

```json
{
  "intercepted": ["move"],
  "timeoutSeconds": 30
}
```

### PUT /api/interactive/config

Replaces the interactive configuration.

```json
{
  "intercepted": ["move", "suction-cup"],
  "timeoutSeconds": 30
}
```

Pass `"intercepted": []` to disable interactive gating.

### GET /api/interactive/pending

Returns the list of pending actions waiting for operator resolution.

```json
{
  "items": [
    {
      "id": "act-0001",
      "robotName": "left",
      "commands": [{"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}}],
      "commandTypes": ["move"],
      "correlationId": "cmd-run-0000-1",
      "createdAt": "2026-04-30T12:00:00+00:00"
    }
  ]
}
```

### POST /api/interactive/{actionId}/resolve

Resolves a pending action. The suspended command response then completes with the
chosen outcome.

Request:

```json
{
  "outcome": "success",
  "reason": "operator approved"
}
```

`outcome` must be `"success"` or `"failure"`; `reason` is optional. Returns
`404 Not Found` if no action with that id exists.

### Events

Two event types accompany interactive mode and appear in `GET /api/events`:

- `PENDING_ACTION` — emitted when a command batch is intercepted and queued.
- `ACTION_RESOLVED` — emitted on operator resolution or timeout.

## WebSocket

### /ws/status

Pushes an initial state snapshot and then event notifications as JSON.

Example message:

```json
{
  "type": "event",
  "event": {
    "id": "evt-1234",
    "type": "STATE",
    "message": "Simulation step update"
  },
  "state": {
    "status": "running",
    "currentPreset": "happy-path",
    "currentStep": 2
  }
}
```

## MQTT

When `SIMULATOR_BROKER_URL` is configured, the distance adapter publishes MQTT messages using the
same payload shape expected by the existing stack.

Topic example:

`sensors/distance/Conveyor/distance_IR_short_left`

Payload example:

```json
{
  "type": "distance_IR_short_left",
  "UID": "TFu",
  "location": "Conveyor",
  "messageID": 1280,
  "distance": 12.5,
  "timestamp": "2026-04-22T12:00:00Z"
}
```

## Event Bridge Configuration

`SIMULATOR_EVENT_BRIDGE` supports `none`, `http`, and `kafka`.

- `none`: no external forwarding
- `http`: POST event payloads to `SIMULATOR_EVENT_BRIDGE_URL`
- `kafka`: reserved for a Kafka-backed bridge in developer environments; the simulator logs the intent and keeps the event history locally in this MVP