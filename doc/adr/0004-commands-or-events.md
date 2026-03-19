# 4. Commands or events

Date: 2026-03-14

## Status

Accepted

## Context

The order process (orchestrator) must trigger the factory and receive its outcome. The customer triggers the order and consumes events from the order process via a dashboard. We need to decide whether to use commands, events, or a mix for this cross-process communication.
Pure commands (request/response) would tightly couple the factory to the order process and reduce its autonomy.  Using pure events to trigger the factory would make it unclear who is in charge of starting the process.

## Decision

The orchestrator sends **commands** to trigger services; services respond with **domain events**.

- The customer sends a `Place Order` command to start the order process.
- The order process sends a `Manufacture Order` command to the factory via Kafka.
- The factory emits domain events on completion: `Manufacturing complete`, `Manufacturing failure`, or `Manufacturing timeout` as Kafka messages.
- The customer dashboard subscribes to order and factory domain events to display the current status.

## Consequences

- The orchestrator retains explicit control while the factory remains a smart endpoint — it emits what happened without knowing what the order process does with it.
- Other services can subscribe to factory events in the future without changes to the factory.
- The factory's start event is coupled to the command's Kafka topic, so schema changes require coordinated updates.
- A correlation key (order ID) must be included in event payloads to route them back to the correct process instance, adding some complexity to the event design.
