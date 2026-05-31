# 15. Embedded H2 Database for Process Engine Persistence

Date: 2026-05-31

## Status

Accepted

## Context

Operaton (see ADR 0003) requires a relational database to persist process instance state, variables, timers, and tasks. We needed to choose between running an external database server or embedding one inside the service.

## Decision

Use H2 as an embedded in-process database in both `order` and `factory`. It starts with the application and requires no external infrastructure beyond a JDBC URL in `application.yml`.

## Consequences

- No additional infrastructure to set up or maintain.
- Process state survives service restarts, allowing in-progress workflows to resume.
- Data does not survive a full environment teardown. Recovery relies on workflow state and the physical state of the factory, not Kafka replay (see ADR 0008).
- Not suitable for horizontal scaling, which is fine given the single-instance constraint of the physical setup (see ADR 0009).
