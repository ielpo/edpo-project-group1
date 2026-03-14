#set document(
  title: [Exercise 3: Process Orchestration \ Exercise 4: Orchestration vs Choreography],
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

= Process Orchestration
The customer will place an order for a furniture using a form, this is the start event for the order process.

#figure(
  image("order_form.png", width: 80%),
  caption: [Order form presented to customer]
)

#figure(
  image("order.png"),
  caption: [Order process]
)

The process will be orchestrated by the order service, which verifies inventory and then commands the factory to manufacture the order.

#figure(
  image("factory.png"),
  caption: [Factory process]
)

The factory process sends events to the customer and order services.

The customer service will display information to the user, this service will be receiving messages from the order and factory processes.

