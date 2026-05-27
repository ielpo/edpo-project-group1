#set document(
  title: "Assignment 2: Stream Processing with Kafka Streams",
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
  Deadline: 01.06.2026, 23:59 \
  Group 1, Team Members: \
  Michael Schütz, Gianluca Ielpo, Eva Amromin
]

#outline()
#pagebreak()

= Project Overview

KAFKEA is an event-driven manufacturing system for custom furniture orders.
In the first assignment, we implemented the core order processing and factory execution logic using Camunda BPMN processes.
A customer can place an order via a Camunda form; the Order service orchestrates the end-to-end process; the Factory service operates the Dobot Magician robot arm. For a full description of the project see the previous reports (Exercises 1–2, 3–4, and 5).

This report covers the stream processing layer added for Assignment 2, implemented in the `kafka-streams` service. The service uses Kafka Streams to process sensor data to restock the existing inventory of KAFKEA: it detects blocks, classifies their colour, and controls the conveyor and robot arm.

To simplify development, the simulator was enhanced to produce synthetic sensor data that mimics the real factory layout. The left conveyor sensor produces distance readings that indicate when a block is present, while the colour sensor produces RGB readings that are classified to determine the block's colour.

#figure(
  image("../images/simulated-factory.png", width: 100%),
  caption: [Simulated factory layout: left (colour) sensor and right (pick-up) sensor]
)

= Stream Processing Implementation

The following sections map the implemented stream processing patterns to the relevant lecture concepts.

== Stateless Operations (Week 8)

Stateless operations transform or filter individual records without requiring any shared state between records.

*Filter* is applied in all three topologies to discard distance readings that do not indicate a block is present. The threshold is `distance < 25.0` (cm), matching the physical range of the conveyor sensors.

*Map / MapValues* is used throughout to translate domain events, for example, wrapping a `BlockPickUpTriggerEvent` into a `RobotArmCommandEvent("PICK_AND_PLACE")` or converting raw RGB values into a `BlockColor` enum.

*Translate (SelectKey)* re-keys streams to the fixed partition keys required for downstream joins and aggregations. For instance, all distance readings are re-keyed to `"distance-sensor"`, and both the block-detected and colour streams are re-keyed to `"sliding-window-join"` before the join.

*Branch* is implemented implicitly: `BlockColorTopology` publishes the `blockPresentStream` both to the `sensor.block-present.v1` topic (consumed by `MoveBlockTopology`) and processes it internally for block detection. This separation of concerns mirrors the branch pattern.

*Enrich* is realised by the stream-stream join in `BlockColorTopology`, which enriches a bare `BlockDetectedEvent` (containing only a UUID and timestamp) with colour information from the colour sensor stream.

== KStream and KTable (Week 9)

All three topologies use both the streaming and table abstractions.

`KStream` is the primary abstraction for unbounded sensor data: distance readings, colour readings, and intermediate events all flow as streams. After the join and reduce, the enriched inventory is materialised into a `KTable` (`inventory-store`), representing the current state of all detected blocks. The table is then converted back to a stream to publish to `inventory.blocks.v1`.

The aggregation state stores in `MoveBlockTopology` (`move-block-edge-store`) and `PickUpBlockTopology` (`pick-up-block-edge-store`) are also KTable-backed, persisting the last-seen timestamp and rising-edge flag per sensor key.

== Joins Across Streams (Week 9)

`BlockColorTopology` joins two independent sensor streams: the block-detected stream, emitting one event per detected block keyed to `"sliding-window-join"`, and the classified colour stream, carrying continuous RGB readings classified to a `BlockColor`, also keyed to `"sliding-window-join"`.

A *stream-stream sliding window join* with a 10-second window (1-second grace) is used, because the block and colour readings are produced at different rates and cannot be perfectly aligned in time. A block may pass the colour sensor slightly before or after the detection event is emitted, so the window accommodates the real-world timing offset.

Both streams are explicitly repartitioned before the join to ensure matching keys land on the same task.

== Interactive Queries (Week 9)

The `inventory-store` KTable is exposed as a queryable state store. The `InventoryQueryController` REST endpoint allows any client to query the current inventory state directly from the Kafka Streams instance, without reading from Kafka topics. `GET /inventory` returns all detected blocks as a cubeId-to-color map; `GET /inventory/{cubeId}` returns the entry for a specific cube.

The controller uses `StoreQueryParameters.fromNameAndType` and `QueryableStoreTypes.keyValueStore()` to access the read-only key-value store at runtime.

== Windowed Operations (Week 10)

*Sliding window join:* The stream-stream join in `BlockColorTopology` uses `JoinWindows.ofTimeDifferenceAndGrace(Duration.ofSeconds(10), Duration.ofSeconds(1))`. This is a sliding window over event time, allowing block and colour events that arrive within 10 seconds of each other to be joined.

*Wall-clock inactivity window (custom processor):* Block detection in `BlockColorTopology` relies on a custom `BlockInactivityProcessor`. A wall-clock punctuation fires every 200 ms and emits a `BlockDetectedEvent` when a sensor key has been quiet for 3 seconds. This implements session-like semantics driven by wall-clock time rather than stream time, which is necessary because physical blocks create a continuous stream of distance readings with no natural end marker.

*Rising-edge aggregation:* `MoveBlockTopology` and `PickUpBlockTopology` use a stateful `aggregate` with a 2-second gap threshold to detect the first reading of a new block. This is conceptually an inactivity-based windowing decision, emitting once per detected presence event after a silence gap.

// TODO: consider adding an explicit tumbling or hopping window aggregation to more directly satisfy the windowed-operations requirement.

== Serialization

All events are serialized and deserialized using a custom `JsonSerde<T>` built on Jackson. This keeps the setup self-contained without requiring a schema registry.

// Avro serialization was not implemented in this assignment.

= Topology Descriptions

== BlockColorTopology

#figure(
  image("../images/kafka-streaming-topology-BlockColorTopology.png", width: 100%),
  caption: [BlockColorTopology: block detection and colour classification]
)

`BlockColorTopology` is the most complex of the three topologies. It detects block presence on the conveyor (distance branch), detects when a block has passed (inactivity processor), classifies the block's colour (colour branch), joins the two observations to produce a `BlockColorEvent`, and maintains a deduplicated inventory of all detected blocks.

The topology reads from two source topics: `sensor.distance.raw.v1` (continuous distance readings from the left sensor) and `sensor.color.raw.v1` (continuous RGB readings from the colour sensor). Both streams are filtered and rekeyed, then joined on the common key `"sliding-window-join"` within a 10-second sliding window. The join output is reduced per `cubeId` to keep only the first colour reading per block, ensuring idempotent inventory updates. The final result is published to `inventory.blocks.v1` and stored in the `inventory-store` KTable.

Additionally, every raw distance reading that indicates a block is present is forwarded to `sensor.block-present.v1`, where it is consumed by `MoveBlockTopology`.

*Justification:* The wall-clock inactivity processor was chosen over a session window because Kafka Streams session windows advance only with new records which could take a significant amount of time in a low-traffic or test environment like KAFKEA restocking. Wall-clock punctuation ensures block detection fires even when the sensor stream stops.

The sliding window join was chosen over a table join because colour events are continuous and not keyed to a specific block identity; temporal proximity is the only way to associate a colour reading with a block.

#figure(
  image("../images/kafka-streaming-topology-BlockColorTopologyTimeline.png", width: 100%),
  caption: [BlockColorTopology: event timeline]
)

== MoveBlockTopology

#figure(
  image("../images/kafka-streaming-topology-MoveBlockTopology.png", width: 60%),
  caption: [MoveBlockTopology: conveyor stop trigger]
)

`MoveBlockTopology` stops the conveyor belt when a block arrives at the left sensor. It reads from `sensor.block-present.v1` (pre-filtered readings published by `BlockColorTopology`) and applies a rising-edge detection via stateful `aggregate`: a `ConveyorCommandEvent("STOP")` is emitted once per block arrival, defined as the first reading after a 2-second absence gap.

*Justification:* Consuming from `sensor.block-present.v1` rather than re-reading the raw distance topic avoids duplicating the filter logic and keeps the topology simple. The rising-edge aggregation prevents a flood of stop commands from a single block that lingers in front of the sensor.

#figure(
  image("../images/kafka-streaming-topology-MoveBlockTopologyTimeline.png", width: 100%),
  caption: [MoveBlockTopology: event timeline]
)

== PickUpBlockTopology

`PickUpBlockTopology` commands the robot arm to pick up and place a block when it arrives at the right sensor. It reads raw distance from `sensor.distance.right.raw.v1`, applies the same `distance < 25.0` filter and rising-edge detection (2-second gap), and emits a `RobotArmCommandEvent("PICK_AND_PLACE")` to `control.robot-arm.commands.v1`.

This topology mirrors the structure of `MoveBlockTopology` but operates on a separate physical sensor and a different output channel (robot arm vs. conveyor). The rising-edge logic is duplicated rather than shared to keep each topology independently deployable and testable.

= ADRs

The following ADRs are related to this assignment:

- ADR 0011: Rising-Edge Detection for Sensor Triggers.
- ADR 0012: Wall-Clock Punctuation for Block Detection.
- ADR 0013: JSON Serialization over Avro.


= Reflections

What we would improve next:

Adding Avro serialization with a schema registry would provide schema evolution guarantees and a more compact wire format.

#pagebreak()

= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Building topologies, Validation against lecture content, Documentation, Presentation],
  [Eva], [Building topologies, Topology implementation, Presentation],
  [Gianluca], [Building topologies, Simulator, Presentation],
)
