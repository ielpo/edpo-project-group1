# 6. Dashboard as a Separate Service

Date: 2026-04-04

## Status

Accepted

## Context

The inventory service initially included a built-in UI for managing the inventory grid. When the requirement arose to show live order progress, we needed to consume Kafka events and push them to the browser in real time. Browsers cannot connect to Kafka directly, so a server-side bridge was required. Adding Kafka consumer and WebSocket logic to the inventory service would mix two unrelated concerns into a service whose sole responsibility is managing stock.

## Decision

Extract the dashboard into a dedicated Spring Boot service (`services/dashboard`, port 8083). This service is responsible for:

- Consuming events from Kafka topics `info.v1` and `error.v1`
- Maintaining WebSocket connections with connected browsers
- Bridging Kafka events to the browser in real time
- Serving the frontend UI (inventory grid + order tracker)

The inventory service remains a pure REST API with no UI responsibilities.

## Consequences

- The dashboard can be deployed, restarted, or scaled independently of the inventory service.
- A failure in the inventory service does not take down the order status view, and vice versa.
- The browser connects to the dashboard service via WebSocket (`/ws/events`) and polls the inventory service directly for grid state.
- One additional service to run and configure.
- The dashboard has no direct access to inventory state; it relies on the inventory REST API and Kafka events only.
