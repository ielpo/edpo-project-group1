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