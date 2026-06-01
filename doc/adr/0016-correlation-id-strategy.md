# 16. Correlation ID Strategy

Date: 2026-05-31

## Status

Accepted

## Context

The order service sends a manufacture command to the factory via Kafka and must resume the correct BPMN process instance when the factory replies. Multiple orders can be in flight at once, and Kafka has no built-in request/reply mechanism.

## Decision

The order service generates a `correlationId` when a process instance starts and includes it in the `Manufacture Order` command. The factory echoes it back in every outcome event. On receipt, the order service uses Operaton's message correlation to resume the matching process instance.

## Consequences

- Process instances are identifiable across async boundaries regardless of how many orders are running.
- The factory only needs to echo the ID it received — it has no knowledge of the order process internals.
- `correlationId` must be present in the command and in all factory outcome events. Omitting it breaks process resumption.
