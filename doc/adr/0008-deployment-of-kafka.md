# 8. Kafka Deployment and Consumer Offset Policy

Date: 2026-04-13

## Status

Accepted

## Context

We needed to decide how Kafka is deployed for the current project scope and how consumers should behave on startup when no committed offset exists.

The system coordinates a physical manufacturing process. Commands on Kafka trigger real-world actions that cannot be safely repeated e.g. replaying an old `order.manufacture.v1` would mean manufacturing an order a second time.

## Decision

Run Kafka as a single-node deployment, one process holding both broker and controller roles. Topics use broker defaults (one partition, replication factor one), matching the single-node setup.

All consumers use `auto.offset.reset=latest`. Recovery after downtime is handled through persisted workflow state and the physical state of the factory, not through Kafka replay.

## Consequences

- Operational complexity stays low, appropriate for the project scope.
- The broker is a single point of failure; a broker failure takes the messaging layer down entirely. Accepted tradeoff.
- `latest` prevents accidental re-execution of commands after a consumer restart. 
- The tradeoff is that messages published while a consumer is down are not seen on reconnect. 
- Moving to a multi-broker cluster will require explicit configuration of partition counts, replication factors and likely a revisit of the offset reset policy.