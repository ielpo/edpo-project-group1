# 4. Commands or events

Date: 2026-03-14

## Status

Accepted

## Context

The order process (orchestrator) must trigger the factory and receive its outcome. For this specific interaction, we need to decide whether to use commands, events, or a mix.

The orchestration boundary is decided in ADR 2.

## Decision

The orchestrator sends **commands** to trigger services and services respond with **domain events**.

- The order process sends a `Manufacture Order` command to the factory service.
- The factory service emits domain events to report manufacturing outcome (`Manufacturing complete` or `Manufacturing failure`).
- Manufacturing timeout is not a factory event. It is handled by a 10-minute BPMN timer in the order process, which then emits an error event.

## Consequences

- The orchestrator retains explicit control while the factory service remains a smart endpoint, it emits what happened without knowing what the order process does with it.
- Additional consumers can subscribe to factory outcome events without requiring changes in the factory service.
- The `Manufacture Order` command schema is a shared contract between order process (producer) and factory service (consumer). Field changes require coordinated evolution (for example explicit versioning and/or schema registry).
- A correlation key (`orderId`) must be present in the `Manufacture Order` command and echoed in factory outcome events so the order process can correlate replies to the correct process instance.
