#set document(
  title: [Exercise 5: Sagas and Stateful Resilience Patterns]
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
  Deadline: 16.04.2026, 23:59 \
  Group 1, Team Members: \
  Michael Schütz, Gianluca Ielpo, Eva Amromin
]

= Stateful resilience patterns
The following resilience patterns are used throughout in the Kafkea Project.

== Stateful retry

If a downstream service is briefly unavailable, we don't want to immediately push that error back to the user.
Instead, we use Operaton's built-in job retry mechanism to handle transient failures automatically.

We applied this in three places:

- Reserving inventory when an order comes in
- Restoring inventory during compensation if something goes wrong
- Fetching components from inventory in the factory process

All three run async with #emph[R3/PT10S], so the engine retries up to three times, ten seconds apart. The retry state is persisted by the workflow engine, meaning it survives restarts. The caller never has to deal with a "try again later" for what's just a temporary issue.

When retries are genuinely exhausted, our workers check if it's the last attempt and raise a proper BPMN error (e.g. #emph[INVENTORY_SERVICE_UNAVAILABLE]), so the process can react through its error or compensation paths.

== Human Intervention Pattern
The human intervention pattern is used for recovery steps that are very hard to fully automate. In our order process, if manufacturing times out or fails, we don't just continue blindly with automation as the state of the physical inventory is unknown. Instead, the process waits in a user task (#emph[Restock inventory], assignee #emph[demo] (used for convenience)) so a person can return the physical inventory to its original state and confirm the action with a tiny Camunda form.

Only after this manual step is completed we continue with the technical restore flow. This keeps process control explicit: automation handles technical issues, while operational recovery is delegated to a human when the situation is too complex to handle for the system.

#pagebreak()

= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Order service, Factory service support, ADRs, Documentation, Presentation],
  [Eva], [Inventory service, Dashboard, Order service support, ADRs, Documentation, Presentation],
  [Gianluca], [Factory and factory service, ADRs, Documentation, Presentation],
)
