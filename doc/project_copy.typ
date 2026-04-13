#set document(
	title: [Project Documentation: Factory Order Flow]
)

#set page(
	paper: "a4",
	numbering: "1/1",
)

#set text(
	font: "Nimbus Sans",
	size: 12pt,
)

#show link: underline

#title()

#align(center)[
	Group 1 \
	Michael Schuetz, Gianluca Ielpo, Eva Amromin
]

#outline()
#pagebreak()

= Project Overview

This project implements an event-driven manufacturing scenario for custom furniture orders.
The project is called #strong[KAFKEA], a blend of #emph[Kafka] and #emph[IKEA].
The core objective is to design and validate how distributed services can coordinate reliably when the business flow spans multiple technical boundaries.

At a business level, we want to achieve three outcomes:

- Customers can place furniture orders and receive transparent status updates from start to completion.
- The system can coordinate inventory reservation, manufacturing by the Dobot Magician robots, and completion reporting across services.
- Failure scenarios (service outage, timeout, partial processing) are handled in a controlled way through retries, error paths, and compensation.

At an architecture level, the project demonstrates a hybrid model:

- #emph[Orchestration] for critical process control (order and factory workflows).
- #emph[Choreography] for status propagation and decoupled consumers (event subscribers such as a read-only dashboard).

The implementation is intentionally close to real distributed-system constraints: remote calls can fail, processes can be long-running, and consistency across services is eventual rather than immediate.
The project therefore focuses not only on the happy path, but also on resilience patterns and recovery.

= Context Map

#figure(
    image("assignments/contextmap.png", width: 70%),
    caption: [Context map]
)

The context map illustrates how the bounded contexts in the system relate to one another. At the core, three domain services handle the primary business flow: #emph[order], #emph[factory], and #emph[inventory].

The responsibilities of these core services are:

- #emph[Order service:] Orchestrates the end-to-end business process. It reserves inventory, sends the manufacturing command, waits for correlated outcome events, enforces timeout handling, and triggers compensation when needed.
- #emph[Factory service:] Executes manufacturing after receiving the order command. It fetches reserved components, controls the assembly workflow, and emits completion or error events.
- #emph[Inventory service:] Owns stock state and reservation lifecycle. It provides REST endpoints to reserve components, fetch reserved positions, and restore stock during compensation paths.

Beyond these, the project includes supporting contexts for visualization and hardware integration. The #emph[dashboard] is a separate service that consumes Kafka status events and serves the live frontend. On the factory side, #emph[color-sensor] (with #emph[color-sensor-fake] as a development/test double) and #emph[dobot-control] provide device integration for the physical manufacturing process.

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
    columns: (18%, 18%, 18%, 24%, 22%),
    table.header([*Service*], [*Consumer Group*], [*Offset Reset*], [*Main Topics*], [*Why configured this way*]),
    [Order], [order-service-correlation], [earliest], [order.complete.v1, error.v1], [Allows recovery/replay for correlation when a group has no committed offsets],
    [Factory], [factory-service], [latest], [order.manufacture.v1], [Factory should process newly issued commands, not historical backlog by default],
    [Dashboard], [dashboard], [latest], [info.v1, error.v1], [UI should show current live status instead of replaying old state after startup],
)

Overall, these Kafka choices prioritize a clear orchestration boundary, straightforward local operability, and robust event correlation over advanced throughput tuning.