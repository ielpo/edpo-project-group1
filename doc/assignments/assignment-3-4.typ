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
  image("contextmap.png", width: 70%),
  caption: [Context map]
)

The context map provides a simplified overview of the main service relationships within the current scope. It currently includes only three services and is intentionally kept minimal, while allowing for easy future extension.

= Process Orchestration

The process begins when a customer places an order for furniture using an order form. This action represents the start event of the overall order process. Currently, the system supports ordering a single item per order; however, it is designed to be extendable to multiple items if time permits.

#figure(
  image("order_form.png"),
  caption: [Order form presented to customer]
)

#figure(
  image("order.png"),
  caption: [Order process]
)

The order process is orchestrated by the order service, which coordinates the workflow by first reserving the required components in the inventory via an HTTP call.
The inventory is implemented as a separate REST service that exposes its API for reservation, restocking and retrieval operations. If the reservation succeeded, the order service sends a command to the factory to initiate the manufacturing process.

#figure(
  image("factory.png"),
  caption: [Factory process]
)

The factory process manufactures the requested item and emits events to inform other services about the progress and completion of the order.

The customer service is responsible for presenting relevant information to the user. It receives updates from both the order service and the factory process and displays the current status of the order to the customer.
