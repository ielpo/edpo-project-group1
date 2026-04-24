#set document(
  title: "Exercise 5: Sagas and Stateful Resilience Patterns",
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

= Project Overview
This project coordinates ordering, inventory, and factory execution, the project overview is shown below.

#figure(
  image("../images/block-diagram.png", width: 80%),
  caption: [Block Diagram]
)

== Successful Order Fulfillment
The diagram shows the normal path from order submission to completion.

#figure(
  image("../images/flow-success.png", width: 100%),
  caption: [Sequence Diagram]
)

== Dobot Control Service

#link("https://github.com/ielpo/edpo-project-group1/tree/main/services/dobot-control")[github.com/ielpo/edpo-project-group1/services/dobot-control]

The robot is controlled via serial using the `pydobotplus` Python library. The existing control service was very limited and did not fulfill the requirements for this project, therefore it was refactored and improved. The new implementation supports a simulation mode, in which the communication with the robot is faked and always succeeds.

Additionally, the service allows to execute individual commands including relative coordinate movements, which are required in order to fetch items in the inventory grid and to place the blocks in the assembly area with precision.

== Color Sensor Service

#link("https://github.com/ielpo/edpo-project-group1/tree/main/services/color-sensor")[github.com/ielpo/edpo-project-group1/services/color-sensor]

#link("https://github.com/ielpo/edpo-project-group1/tree/main/services/color-sensor-fake")[github.com/ielpo/edpo-project-group1/services/color-sensor-fake]

The existing color sensor of the Dobot system is very limited and only returns a boolean for each color, rendering the detection of all four colors infeasible.
To mitigate these issues, a new color sensor was implemented on a raspberry pi pico using a TCS34725. The WiFi interface on the Pico allows the color sensor to offer a REST interface.

To ease debugging and automated testing, a fake color sensor service is implemented in Rust.

#figure(
  image("../images/color-sensor.png", width: 20%),
  caption: [Color Sensor]
)


== Distance Sensor

The distance sensor is part of the Tinkerforge setup, and publishes messages over MQTT after each measurement. The distance is used to detect if a block was picked up, and avoid issues where the block is lost during transfer or the inventory service had a wrong internal state compared to the physical inventory.


= Stateful resilience patterns

The following resilience patterns are used throughout the Kafkea Project.

== Stateful retry

If a downstream service is briefly unavailable, we don't want to immediately push that error back to the user.
Instead, we use Operaton's built-in job retry mechanism to handle transient failures automatically.

We applied this in three places in the Order process:

- #emph[Reserve inventory] — when an order comes in
- #emph[Reset inventory] — during compensation after a timeout
- #emph[Reset inventory] — during compensation after a manufacturing error

All three run async with #emph[R3/PT10S], so the engine retries up to three times, ten seconds apart. The retry state is persisted by the workflow engine, meaning it survives restarts. The caller never has to deal with a "try again later" for what's just a temporary issue.

When retries are genuinely exhausted, our workers check if it's the last attempt and raise a proper BPMN error (e.g. #emph[INVENTORY_SERVICE_UNAVAILABLE]), so the process can react through its error or compensation paths.

== Human Intervention Pattern

The human intervention pattern is used for recovery steps that are very hard to fully automate. In our order process, if manufacturing times out or fails, we don't just continue blindly with automation as the state of the physical inventory is unknown. Instead, the process waits in a user task (#emph[Restock inventory], assignee #emph[demo] (used for convenience)) so a person can return the physical inventory to its original state and confirm the action with a tiny Camunda form.

Only after this manual step is completed we continue with the technical restore flow. This keeps process control explicit: automation handles technical issues, while operational recovery is delegated to a human when the situation is too complex to handle for the system. As a simplification, the process then ends with an error rather than restarting the order.

== Epic Saga Pattern

The overall flow follows the traditional #emph[Epic Saga] idea with one clear orchestrator. In our case, the Order service coordinates the transaction-like business request and monitors whether all required steps complete.

If a later step fails, we do not leave already performed actions as-is. Instead, we trigger compensating actions (most importantly inventory restore) to reverse earlier writes inside the distributed transaction scope. However, true transaction isolation across services is not guaranteed as intermediate state changes may be visible to other parts of the system before a rollback occurs, and compensating actions themselves could potentially fail.

= Lessons Learned

- Human intervention is essential for systems like ours where real-world state cannot always be reconstructed from software state alone.
- Being able to develop software independently from the hardware is of advantage, it allows for quicker iteration.
- Error handling by Operaton requires to throw specific exeptions, else the retry mechanism is triggered. In our case this led to the factory trying to fetch blocks for the same order multiple times.


= Reflections

What worked well:

- Separating orchestration logic (Order) from execution logic (Factory) kept responsibilities understandable.
- Combining automation with manual checkpoints made recovery more realistic for physical processes.
- The services were implemented individually and tested in isolation, which made development more manageable and allowed us to validate each part before integration.
- The integration was straightforward due to the clear contract of Kafka topics and REST APIs.
- Hexagonal Architecture worked very well for keeping boundaries and dependencies explicit.

What was challenging:

- The initial Camunda setup was a bit tricky to get right due to all the different required dependencies and configurations.
- Most of the project has fairly little business logic while Hexagonal Architecture required many interfaces and adapters, which felt like substantial boilerplate.
- Access to the lab is limited, limiting the time spent developing with hardware.

What we would improve next:

- Replace fixed retry policies with context-aware retry/backoff per failure type.
- Add more details to the Kafka events (e.g. failure reasons, retry counts) to support better observability and debugging. This would have also made the dashboard simpler to implement.
- Add testing (unit and integration).
- Implement a proper simulation mode for the factory that can be used for automated testing.

#pagebreak()

= ADRs
The following ADRs are related to this exercise:

- ADR 0009: Granularity of Factory Service

= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Order service, Factory service support, ADRs, Documentation, Presentation],
  [Eva], [Inventory service, Dashboard, Order service support, ADRs, Documentation, Presentation],
  [Gianluca], [Factory and factory service, ADRs, Documentation, Presentation],
)
