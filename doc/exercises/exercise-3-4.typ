#set document(
title: "Exercise 3: Process Orchestration \n Exercise 4: Orchestration vs Choreography",
)

#set page(
paper: "a4",
numbering: "1/1")

#set text(
font: "Nimbus Sans",
size: 12pt
)

#show link: underline

#title()

#align(center)[
  Deadline: 17.03.2026, 23:59 \
  Group 1, Team Members: \
  Michael Schütz, Gianluca Ielpo, Eva Amromin
]

#outline()
#pagebreak()

= Overview

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

= Architecture Characteristics

The following architecture characteristics were identified as the most relevant driving qualities for KAFKEA.
They reflect the system's core constraints as a distributed, event-driven manufacturing platform where correctness, resilience, and availability are non-negotiable.

#table(
  columns: (22%, 78%),
  table.header([*Characteristic*], [*Relevance to KAFKEA*]),
  [*Fault Tolerance*],
  [The system must continue operating when individual components fail. KAFKEA handles this through BPMN error paths, timeout boundaries, retries, and compensation flows, for example restocking inventory when manufacturing fails.],
  [*Data Consistency*],
  [State is distributed across Order, Inventory, and Factory services with no shared database. Consistency is eventual and maintained through correlated Kafka events and persisted workflow state rather than synchronous transactions.],
  [*Interoperability*],
  [KAFKEA integrates heterogeneous technologies: HTTP REST between services, Kafka for async messaging, a BPMN engine for process control, a serial port connection to the Dobot robot arm, and a color sensor running on a Raspberry Pi Pico. Each boundary requires a deliberate integration contract.],
  [*Reliability*],
  [Manufacturing commands and status events must not be lost. KAFKEA relies on Kafka's durability guarantees and BPMN engine persistence to ensure that every order reaches a defined outcome, even across restarts.],
  [*Availability*],
  [The system must remain accessible to customers during operation. The current single-node Kafka setup is a deliberate tradeoff for development simplicity; production-grade availability would require a multi-broker cluster with higher replication factors.],
)

= Context Map

#figure(
  image("../images/contextmap.png", width: 70%),
  caption: [Context map]
)

The context map shows how the bounded contexts in the KAFKEA system relate to one another. At the core, three domain services handle the primary business flow: #emph[order], #emph[factory], and #emph[inventory]. Supporting contexts cover visualization (#emph[dashboard]) and hardware integration (#emph[dobot-control], #emph[color-sensor]).

= Architecture

== Kafka Communication Design

Kafka is used for cross-service communication whenever the interaction should be asynchronous and decoupled. We intentionally separate command-style and event-style topics:

- #emph[order.manufacture.v1] is a command topic from Order to Factory.
- #emph[order.complete.v1], #emph[info.v1], and #emph[error.v1] are event topics.

This follows the design principle that orchestrators issue commands, while services publish what happened as events.

=== Topic Overview and Rationale

#table(
    columns: (24%, 18%, 15%, 15%, 28%),
    table.header([*Topic*], [*Purpose*], [*Produced by*], [*Consumed by*], [*Why this topic exists*]),
    [order.manufacture.v1], [Start manufacturing for an accepted order], [Order], [Factory], [Keeps factory startup explicit and controlled by the order orchestrator],
    [order.complete.v1], [Manufacturing completed successfully], [Factory], [Order, Dashboard], [Lets order process continue asynchronously and lets UI update without tight coupling],
    [info.v1], [Informational status events], [Order, Factory], [Dashboard], [Provides user-facing progress updates as a separate concern],
    [error.v1], [Failure and timeout status events], [Order, Factory], [Order, Dashboard], [Consolidates failure communication and supports correlation back to running processes],
)

=== Broker and Cluster Setup

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

=== Partitions, Keys, and Ordering

Topic partition counts are not explicitly provisioned by project code, so they follow broker defaults in this environment: by default, auto-created topics use #emph[1 partition] (Kafka #emph[num.partitions=1] default).

Replication is effectively #emph[1] in this project because Kafka runs with a single broker; the internal offsets topic is also configured with replication factor #emph[1].

Current producer strategy uses no explicit business keying for topic routing.

Why we chose this:

- For this workload, correlation relies on payload fields (#emph[orderId], #emph[correlationId]) rather than partition-based routing.
- It keeps producer logic simple while still enabling deterministic process correlation in the orchestrator.

Implication:

- Kafka ordering guarantees remain #emph[per partition], not global across topics.

=== Consumer Groups and Offset Reset Policies

#table(
    columns: (24%, 26%, 18%, 32%),
    table.header([*Service*], [*Consumer Group*], [*Offset Reset*], [*Main Topics*]),
    [Order], [order-service-correlation], [latest], [order.complete.v1, error.v1],
    [Factory], [factory-service], [latest], [order.manufacture.v1],
    [Dashboard], [dashboard], [latest], [info.v1, error.v1],
)

All consumers are configured with #emph[latest] because this system processes live workflow traffic and does not rely on startup replay from Kafka history. In this setup, replaying backlog would mostly re-emit stale status updates and historical command/events, while process correlation and recovery are handled through persisted workflow state and service data stores.

== ADRs

The architecture is grounded in the following accepted ADRs:

- #link("../adr/0001-record-architecture-decisions.md")[ADR 0001]: Record architecture decisions using ADRs.
- #link("../adr/0002-orchestration-vs-choreography.md")[ADR 0002]: Use orchestration for order/manufacturing and choreography for customer-facing updates.
- #link("../adr/0003-operaton-as-bpmn-engine.md")[ADR 0003]: Use Operaton as BPMN engine.
- #link("../adr/0004-commands-or-events.md")[ADR 0004]: Use commands to trigger services and events to report outcomes.
- #link("../adr/0005-item-color-owned-by-inventory.md")[ADR 0005]: Inventory is the source of truth for item color.
- #link("../adr/0006-dashboard-as-separate-service.md")[ADR 0006]: Dashboard is a separate service for event visualization.
- #link("../adr/0007-structure-of-kafka-topics.md")[ADR 0007]: Structure of the Kafka topics.

= Process Orchestration

The process begins when a customer fills out the order form seen in @order-form. This action represents the start event of the overall order process. Currently, the system supports ordering a single item in a selected colour per order; however, it is designed to be extendable to multiple items if time permits.

#figure(
  image("../images/order_form.png"),
  caption: [Order form presented to customer]
) <order-form>

== Order Service
The order service orchestrates the end-to-end business process by coordinating the
workflow.
As seen in @order-process, the order service first reserves the required components in inventory via an HTTP call, then sends the manufacturing command, waits for correlated outcome events, enforces timeout handling, and triggers compensation when needed.

#figure(
  image("../images/order.png"),
  caption: [Order process]
) <order-process>


== Inventory Service

The inventory ows stock state ad the reservation lifecycle. It is implemented as a separate REST service that exposes its API for reservation, restocking and retrieval operations. If the reservation succeeded, the order service sends a command to the factory to initiate the manufacturing process.

== Factory Service
The factory process manufactures the requested item and emits events to inform other services about the progress and completion of the order.

#figure(
  image("../images/factory.png"),
  caption: [Factory process]
)

== Dashboard Service
The dashboard service is responsible for presenting relevant information to the user. It receives updates from both the order service and the factory process and displays the current status of the order to the customer.

== Dobot Control
Communicates with the Dobot using the serial port and provides a REST API to send commands to the physical robot arm.

== Color Sensor
Runs on a RaspberryPi Pico and controls and reads out color using a TDSxxx color sensor. A #emph[color-sensor-fake] variant is available as a development/test double.


#pagebreak()
= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Model processes, Report],
  [Eva], [Model processes, ADRs],
  [Gianluca], [Model processes, ADRs, Report],
)
