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

= Context Map

#figure(
  image("../images/contextmap.png", width: 70%),
  caption: [Context map]
)


The context map shows how the bounded contexts in the KAFKEA system relate to one another. At the core, three domain services handle the primary business flow: #emph[order], #emph[factory], and #emph[inventory].

The responsibilities of these core services are:

- #emph[Order service:] Orchestrates the end-to-end business process. It reserves inventory, sends the manufacturing command, waits for correlated outcome events, enforces timeout handling, and triggers compensation when needed.
- #emph[Factory service:] Executes manufacturing after receiving the order command. It fetches reserved components, controls the assembly workflow, and emits completion or error events.
- #emph[Inventory service:] Owns stock state and reservation lifecycle. It provides REST endpoints to reserve components, fetch reserved positions, and restore stock during compensation paths.

Beyond these, the project includes supporting contexts for visualization and hardware integration. The #emph[dashboard] is a separate service that consumes Kafka status events and serves the live frontend. On the factory side, #emph[color-sensor] (with #emph[color-sensor-fake] as a development/test double) and #emph[dobot-control] provide device integration for the physical manufacturing process.

= Process Orchestration

The process begins when a customer places an order for furniture using an order form. This action represents the start event of the overall order process. Currently, the system supports ordering a single item in a selected colour per order; however, it is designed to be extendable to multiple items if time permits.

#figure(
  image("../images/order_form.png"),
  caption: [Order form presented to customer]
)

#figure(
  image("../images/order.png"),
  caption: [Order process]
)

The order process is orchestrated by the order service, which coordinates the workflow by first reserving the required components in the inventory via an HTTP call.
The inventory is implemented as a separate REST service that exposes its API for reservation, restocking and retrieval operations. If the reservation succeeded, the order service sends a command to the factory to initiate the manufacturing process.

#figure(
  image("../images/factory.png"),
  caption: [Factory process]
)

The factory process manufactures the requested item and emits events to inform other services about the progress and completion of the order.

The customer service is responsible for presenting relevant information to the user. It receives updates from both the order service and the factory process and displays the current status of the order to the customer.

= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Model processes, Report],
  [Eva], [Model processes, ADRs],
  [Gianluca], [Model processes, ADRs, Report],
)
