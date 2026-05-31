# 14. Hexagonal Architecture for Order and Factory Services

Date: 2026-05-31

## Status

Accepted

## Context

The order and factory services integrate with multiple external systems: Kafka, Operaton, and several REST APIs. Without a clear structure, infrastructure concerns such as Kafka wiring, BPMN delegates, and REST clients risk leaking into business logic.

## Decision

Both services follow hexagonal (ports and adapters) architecture. Business logic lives in `application/service/`, isolated behind port interfaces in `application/port/in/` and `application/port/out/`. Inbound adapters (Kafka consumers, Operaton delegates) and outbound adapters (REST clients, Kafka publishers) live in `adapters/`.

## Consequences

- Business logic can be tested without Kafka, Operaton, or any REST dependency.
- Operaton delegates in `adapters/in/` translate BPMN steps into use case calls, keeping the process engine out of the application layer.
- Adds some structural overhead for a small codebase, but the separation becomes worthwhile when integrating multiple protocols at once.
