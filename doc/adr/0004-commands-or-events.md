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
- The order process sends a `Manufacture Order` command to the factory service via Kafka (topic: `order.manufacture.v1`).
- The factory service emits domain events on completion: `Manufacturing complete` (topic: `order.complete.v1`) or `Manufacturing failure` (topic: `error.v1`).
- Manufacturing timeout is not a factory event — it is handled by a 3-minute BPMN timer inside the order process. On expiry, the order process itself publishes an `error.v1` event.
- The order process publishes status events to the `info.v1` and `error.v1` topics; the customer dashboard subscribes to these to display the current order status.

This design reflects two kinds of coupling discussed in the course (cf. Lecture 4, Slide 23):
- **Commands — sender decides to couple:** The order process (orchestrator) explicitly knows about and addresses the factory service. It owns the decision to couple.
- **Events — receiver decides to couple:** The factory service emits what happened without knowing who listens. The order process and the customer dashboard independently decide to subscribe to factory events on their own terms. The factory remains unaware of its consumers.

This hybrid approach gives the orchestrator explicit control over process flow while keeping the factory a self-contained smart endpoint.

## Consequences

- The orchestrator retains explicit control while the factory service remains a smart endpoint — it emits what happened without knowing what the order process does with it.
- The customer dashboard and any future services can subscribe to factory events without changes to the factory service.
- The `Manufacture Order` command schema on topic `order.manufacture.v1` is shared between the order process (producer) and the factory service (consumer). Any field addition or removal requires a coordinated deployment of both sides. A schema registry (e.g., Confluent Schema Registry with Avro) or an explicit versioning strategy would be needed to manage this safely.
- A correlation key (`order_id`) must be included in event payloads to route responses back to the correct process instance. Specifically:
  - The `Manufacture Order` command (sent by the orchestrator on `order.manufacture.v1`) must include the `order_id`.
  - Both factory domain events (`Manufacturing complete` on `order.complete.v1` and `Manufacturing failure` on `error.v1`) must echo back the `order_id`.
  - The `OrderCompleteEventConsumer` and `ErrorEventConsumer` in the order service use the `order_id` to correlate the Kafka message back to the correct running BPMN process instance via `CamundaMessageCorrelationAdapter`.
