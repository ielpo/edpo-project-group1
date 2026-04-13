= Architecture

== Context Map

#figure(
	image("../images/contextmap.png", width: 78%),
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
