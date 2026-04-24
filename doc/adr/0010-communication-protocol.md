# 10. Communication Protocol per Integration

Date: 2026-04-24

## Status

Accepted

## Context

The system integrates very different communication partners:

- Internal business services
- Web-based UI
- Network-connected hardware

A single protocol for all integrations would either add unnecessary complexity for browser and CRUD-style interactions, or create avoidable request/response overhead for streaming hardware signals.

Existing implementation constraints also matter:

- The existing Dobot control is implemented as REST.
- Tinkerforge already publishes sensor data via MQTT.
- Inventory must be usable by backend services and our web-based UI through one stable interface.

## Decision

Use a protocol per integration boundary, not one protocol for everything:

- **Inventory API: REST/HTTP**
  - One interface for both backend services and HTML frontend.
  - Simple request/response semantics for reserve, fetch, restore and grid reads.
- **Dobot control: REST/HTTP**
  - New implementation aligned with the existing REST contract.
- **Tinkerforge telemetry: MQTT**
  - Matches existing publisher behavior.
  - Event stream fits pub/sub and decoupled consumers.
- **Color sensor over network: MQTT**
  - Low overhead for frequent sensor messages.
  - Asynchronous publish/subscribe avoids blocking request/reply waits and supports multiple consumers.

## Consequences

- Protocol choice matches the nature of each integration and reduces accidental complexity.
- Inventory remains easy to consume from browser code and backend code through one HTTP contract.
- Sensor paths (Tinkerforge and color sensor) become event-oriented and scalable for additional subscribers.
- The system operates multiple protocols (HTTP + MQTT), so operations and monitoring must cover both.