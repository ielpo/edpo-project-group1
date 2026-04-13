= Architecture

== Context Map
// Insert context map

== Block Diagran
// Insert block diagram with actual services

== ADRs

The architecture is grounded in the following accepted ADRs:

- #link("../adr/0001-record-architecture-decisions.md")[ADR 0001]: Record architecture decisions using ADRs.
- #link("../adr/0002-orchestration-vs-choreography.md")[ADR 0002]: Use orchestration for order/manufacturing and choreography for customer-facing updates.
- #link("../adr/0003-operaton-as-bpmn-engine.md")[ADR 0003]: Use Operaton as BPMN engine.
- #link("../adr/0004-commands-or-events.md")[ADR 0004]: Use commands to trigger services and events to report outcomes.
- #link("../adr/0005-item-color-owned-by-inventory.md")[ADR 0005]: Inventory is the source of truth for item color.
- #link("../adr/0006-dashboard-as-separate-service.md")[ADR 0006]: Dashboard is a separate service for event visualization.
- #link("../adr/0007-structure-of-kafka-topics.md")[ADR 0007]: Structure of the Kafka topics.
