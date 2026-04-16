# 7. Kafka Topic Structure

Date: 2026-04-13

## Status

Accepted

## Context

The system uses Kafka for asynchronous cross-service communication. We needed a convention for organizing topics that makes ownership and data flow direction clear, and that distinguishes between messages directed at a specific service and messages broadcast to any interested consumer.

## Decision

Separate topics by intent into **commands** and **events**:

- **Commands** are issued by an orchestrator to a specific service to trigger work (e.g. `order.manufacture.v1`, Order → Factory).
- **Events** are published by services to announce outcomes or status, consumed by one or more subscribers (e.g. `order.complete.v1`, `info.v1`, `error.v1`).

Topics follow a `<domain>.<intent>.v1` naming convention, with the version suffix reserved for future schema evolution.

Producers do not use explicit partition keys. Correlation across related messages relies on payload fields (`orderId`, `correlationId`) rather than partition-based routing.

## Consequences

- Topic ownership and data flow direction are immediately clear from naming and the command/event distinction.
- Adding new event consumers requires no changes to producers.
- Without partition keying, per-partition ordering guarantees cannot be relied on across related messages; ordering must be handled at the application level.
- The `v1` suffix creates a clear migration path for breaking schema changes (introduce `v2`, run both in parallel, retire `v1`).