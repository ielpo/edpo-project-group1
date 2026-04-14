= Architecture

= Kafka Communication Design

Kafka is used for cross-service communication whenever the interaction should be asynchronous and decoupled. We intentionally separate command-style and event-style topics:

- #emph[order.manufacture.v1] is a command topic from Order to Factory.
- #emph[order.complete.v1], #emph[info.v1], and #emph[error.v1] are event topics.

This follows the design principle that orchestrators issue commands, while services publish what happened as events.

== Topic Overview and Rationale

#table(
    columns: (24%, 18%, 15%, 15%, 28%),
    table.header([*Topic*], [*Purpose*], [*Produced by*], [*Consumed by*], [*Why this topic exists*]),
    [order.manufacture.v1], [Start manufacturing for an accepted order], [Order], [Factory], [Keeps factory startup explicit and controlled by the order orchestrator],
    [order.complete.v1], [Manufacturing completed successfully], [Factory], [Order, Dashboard], [Lets order process continue asynchronously and lets UI update without tight coupling],
    [info.v1], [Informational status events], [Order, Factory], [Dashboard], [Provides user-facing progress updates as a separate concern],
    [error.v1], [Failure and timeout status events], [Order, Factory], [Order, Dashboard], [Consolidates failure communication and supports correlation back to running processes],
)

== Broker and Cluster Setup

The project currently runs Kafka as a local #emph[single-node KRaft] setup:

- one process with both broker and controller role,
- advertised listener `PLAINTEXT://localhost:9092`,
- offsets topic replication factor #emph[1].

Why we chose this:

- It minimizes operational complexity for local development and demos.
- It is sufficient for the project scale and assignment scope.
- It keeps deployment friction low while preserving real Kafka semantics.

Tradeoff:

- This setup is not fault-tolerant at broker level; production-grade high availability would require multiple brokers and a higher replication factor.

== Partitions, Keys, and Ordering

Topic partition counts are not explicitly provisioned by project code, so they follow broker defaults in this environment: by default, auto-created topics use #emph[1 partition] (Kafka #emph[num.partitions=1] default).

Replication is effectively #emph[1] in this project because Kafka runs with a single broker; the internal offsets topic is also configured with replication factor #emph[1].

Current producer strategy uses no explicit business keying for topic routing.

Why we chose this:

- For this workload, correlation relies on payload fields (#emph[orderId], #emph[correlationId]) rather than partition-based routing.
- It keeps producer logic simple while still enabling deterministic process correlation in the orchestrator.

Implication:

- Kafka ordering guarantees remain #emph[per partition], not global across topics.

== Consumer Groups and Offset Reset Policies

#table(
    columns: (24%, 26%, 18%, 32%),
    table.header([*Service*], [*Consumer Group*], [*Offset Reset*], [*Main Topics*]),
    [Order], [order-service-correlation], [latest], [order.complete.v1, error.v1],
    [Factory], [factory-service], [latest], [order.manufacture.v1],
    [Dashboard], [dashboard], [latest], [info.v1, error.v1],
)

All consumers are configured with #emph[latest] because this system processes live workflow traffic and does not rely on startup replay from Kafka history. In this setup, replaying backlog would mostly re-emit stale status updates and historical command/events, while process correlation and recovery are handled through persisted workflow state and service data stores.


== Block Diagrams
// Insert block diagram with actual services => what does this even mean?

== ADRs

The architecture is grounded in the following accepted ADRs:

- #link("../adr/0001-record-architecture-decisions.md")[ADR 0001]: Record architecture decisions using ADRs.
- #link("../adr/0002-orchestration-vs-choreography.md")[ADR 0002]: Use orchestration for order/manufacturing and choreography for customer-facing updates.
- #link("../adr/0003-operaton-as-bpmn-engine.md")[ADR 0003]: Use Operaton as BPMN engine.
- #link("../adr/0004-commands-or-events.md")[ADR 0004]: Use commands to trigger services and events to report outcomes.
- #link("../adr/0005-item-color-owned-by-inventory.md")[ADR 0005]: Inventory is the source of truth for item color.
- #link("../adr/0006-dashboard-as-separate-service.md")[ADR 0006]: Dashboard is a separate service for event visualization.
- #link("../adr/0007-structure-of-kafka-topics.md")[ADR 0007]: Structure of the Kafka topics.
