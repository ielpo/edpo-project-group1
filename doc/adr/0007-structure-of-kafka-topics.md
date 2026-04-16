# 7. Structure of Kafka Topics

Date: 2026-04-13

## Status

Accepted

## Context

The system uses Kafka for asynchronous cross-service communication. We needed a convention for how topics are organized, what role each topic plays, and how to distinguish between commands directed at a specific service and events broadcast to multiple consumers.

## Decision

Separate Kafka topics by intent into commands and events.

- **Command topic:** `order.manufacture.v1`: issued by the order orchestrator to the factory service.
- **Event topics:** `order.complete.v1`, `info.v1`, `error.v1`: published by services to announce outcomes or status, consumed by one or more subscribers.

Topics follow a `<domain>.<intent>.v1` naming convention with versioning embedded for future schema evolution.

- Producers do not use explicit partition keys; correlation relies on payload fields (`orderId`, `correlationId`).
- Topics use broker defaults: one partition, replication factor one (matching the single-node KRaft setup).
- Consumer offset reset is configured per role: `earliest` for the order service (replay/correlation recovery), `latest` for factory and dashboard (current commands and live status only).

## Consequences

- Topic ownership and data flow direction are immediately clear from naming and the command/event distinction.
- Adding new event consumers requires no changes to producers.
- Without explicit partition keying, per-partition ordering guarantees cannot be relied on across related messages; ordering must be handled at the application level.
- The `latest` offset reset for factory means commands published during factory downtime are missed unless additional recovery logic is added.
- If the system moves to a multi-broker cluster, partition counts and replication factors will need explicit configuration.