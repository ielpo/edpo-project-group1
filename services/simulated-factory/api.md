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