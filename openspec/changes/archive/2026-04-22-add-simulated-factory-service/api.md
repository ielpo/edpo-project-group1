# Simulated Factory Service API (v1)

This document defines the minimal REST/WebSocket/MQTT contracts the `simulated-factory-service` exposes for developer workflows. Keep the contract stable: consumers (e.g. `dobot-control`) must be able to use these endpoints without change.

Version: v1

---

## HTTP API

Base path: `/api` (service root)

### GET /api/status
- Description: Returns current `SimulationState`.
- Response 200 JSON:
  {
    "id": "run-0001",
    "status": "idle|running|stopped",
    "currentPreset": "happy-path",
    "currentStep": 3,
    "timestamp": "2026-04-22T12:00:00Z"
  }

### POST /api/simulations/run
- Description: Start a deterministic run of a named preset.
- Request JSON:
  { "preset": "happy-path", "speed": "normal" }
- Response: 202 Accepted
  { "runId": "run-0001", "status": "accepted" }
- Notes: Handler should be non-blocking; run executes asynchronously.

### POST /api/simulations/stop
- Description: Stop the active run.
- Request: none
- Response 200 or 202: { "status": "stopping" }

### POST /api/simulations/reset
- Description: Reset simulation to initial state.
- Response 200: { "status": "reset" }

### GET /api/config/sensors
- Description: Return current sensor configs.
- Response 200 JSON: [ { "sensorId": "color-left", "mode": "fixed", "value": "RED" }, ... ]

### PUT /api/config/sensors/{sensorId}
- Description: Update sensor behavior.
- Request JSON:
  { "mode": "fixed|random|scripted", "value": "RED", "failRate": 0.0 }
- Response 200: updated config

### GET /api/events
- Description: Paginated chronological event log (in-memory). Events include REST requests, MQTT publishes, and optionally Kafka events produced by the simulator.
- Query: `?page=1&pageSize=50&filter=type:MQTT` (optional)
- Response 200: { "items": [ {"ts":"...","type":"MQTT","topic":"...","payload":{...} }, ... ], "nextPage": 2 }

### POST /api/dobot/{name}/commands
- Description: Forward one or more Dobot commands (movement, suction, conveyor). Used by `DobotFake` when forwarding UI/recording information.
- Request JSON: either a single command or an array of commands.
  Example single command:
  { "type": "move", "target": { "x": 100, "y": 200, "z": 50 }, "speed": 50 }
- Response: 202 Accepted
  { "correlationId": "c-1234" }
- Notes: Commands may be accepted for execution; commands should not block the caller.

### GET /api/dobot/{name}/color
- Description: Return color read by the simulated Dobot sensor.
- Response 200 JSON:
  { "color": "RED", "raw_color": [1,0,0], "timestamp": "..." }

### GET /api/dobot/{name}/ir
- Description: Return IR detection state (true/false).
- Response 200 JSON: { "ir": true }

### GET /api/dobot/{name}/state
- Description: Return current simulated Dobot state (position/speed/conveyor state).
- Response 200 JSON: { "position": {"x":0,"y":0,"z":0}, "speed": 50, "conveyor": "running" }

### POST /api/events
- Description: Accept simulator-origin events for UI correlation or for forwarding to event bridge.
- Request JSON: { "type": "movement", "payload": { ... }, "ts": "..." }
- Response 202 Accepted

---

## WebSocket

### /ws/status
- Streams JSON messages with either full state snapshots or incremental diffs.
- Message example:
  { "type": "state_diff", "patch": { "currentStep": 4 } }
- Use: UI subscribes to live updates; allow simple JSON messages only.

---

## MQTT

Distance sensor publishing (Tinkerforge-compatible) — simulator may publish these messages directly to a configured broker.

- Topic example: `sensors/distance/Conveyor/distance_IR_short`
- Message shape (JSON):
  {
    "type": "distance_IR_short",
    "UID": "2a7C",
    "location": "Conveyor",
    "messageID": 1273,
    "distance": 30.0,
    "timestamp": "2026-04-22T12:00:00Z"
  }
- Broker: configurable via `SIMULATOR_BROKER_URL` / environment.
- Cadence: configurable per-sensor (presets can override cadence).

---

## HTTP semantics and timeouts

- Endpoints used by other services (e.g. `GET /api/dobot/{name}/color`) should respond quickly; clients should use short timeouts (e.g., 500ms–2s) and have clear fallback behavior if the simulator is unreachable.
- Commands endpoints accept requests asynchronously (202) and provide correlation IDs where appropriate.

---

## Compatibility notes

- Keep endpoint paths and response shapes compatible with the real hardware service contracts used by `dobot-control` and the color sensor service. If exact shapes differ, document translation behavior in `simulator_client` adapter.

---

## Versioning

- Start at `v1`. If breaking changes are required later, introduce `/v2/` prefixed routes and keep `v1` for backward compatibility.

---

## Examples

Start a happy-path run:

```http
POST /api/simulations/run
Content-Type: application/json

{ "preset": "happy-path" }
```

Read color from left dobot:

```http
GET /api/dobot/left/color
```

MQTT sample publish (distance):

Topic: `sensors/distance/Conveyor/distance_IR_short`
Payload: see message shape above.

---

File: services/simulated-factory/api.md (this change adds the spec under the openspec change directory)
