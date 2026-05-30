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

#set heading(numbering: "1.1.")

#show link: underline

#title()

#align(center)[
  Deadline: 01.06.2026, 23:59 \
  Group 1, Team Members: \
  Michael Schütz, Gianluca Ielpo, Eva Amromin
]

#outline()
#pagebreak()

= Changes to Assignment 1

Since the hand-in of Assignment 1, the documentation for Exercise 5 has been updated. ADR 0010 was added to document the decisions around communication protocols.
The flow-success sequence diagram was extended for clarity, accompanied by additional explanatory text.

= Project Overview

KAFKEA is an event-driven manufacturing system for custom furniture orders.
In the first assignment, we implemented the core order processing and factory execution logic using Camunda BPMN processes.
A customer can place an order via a Camunda form. The Order service orchestrates the end-to-end process. The Factory service operates the Dobot Magician robot arm. For a full description of the project see the previous reports (Exercises 1–2, 3–4, and 5).

This report covers the stream processing layer added for Assignment 2, implemented in the `kafka-streams` service. The service uses Kafka Streams to process sensor data to restock the existing inventory of KAFKEA: it detects blocks, classifies their colour, and controls the conveyor and robot arm.


The new service resides in the inventory bounded context. Because the inventory is now being restocked by the Dobot Magician robot, the Dobot Magician control is now a shared kernel between the the inventory and factory contexts.

#figure(
  image("../images/contextmap-assignment2.png", width: 70%),
  caption: [Updated context map]
)

To simplify development, the simulator was enhanced to produce synthetic sensor data that mimics the real factory layout. The left conveyor sensor produces distance readings that indicate when a block is present, while the colour sensor produces RGB readings that are classified to determine the block's colour.

#figure(
  image("../images/simulated-factory.png", width: 100%),
  caption: [Simulated factory layout: left (colour) sensor and right (pick-up) sensor]
)

The following table lists the Kafka topics consumed and produced by the `kafka-streams` service.

#figure(
  table(
    columns: (38%, 17%, 45%),
    table.header([*Topic*], [*Direction*], [*Purpose*]),
    [`sensor.distance.raw.v1`],    [in],      [Raw distance readings from the left conveyor sensor (Factory service via MQTT)],
    [`sensor.distance.right.raw.v1`], [in],   [Raw distance readings from the right conveyor sensor (Simulator)],
    [`sensor.color.raw.v1`],       [in],      [Raw RGB readings from the colour sensor (Factory service)],
    [`sensor.block-present.v1`],   [internal],[Filtered block-present readings forwarded from BlockColorTopology to MoveBlockTopology],
    [`inventory.blocks.v1`],       [out],     [Enriched block and colour events; also queryable via `GET /inventory`],
    [`control.conveyor.commands.v1`], [out],  [Conveyor stop commands emitted by MoveBlockTopology],
    [`control.robot-arm.commands.v1`], [out], [Robot arm pick-and-place commands emitted by PickUpBlockTopology],
  ),
  caption: [Kafka topics consumed and produced by the kafka-streams service],
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

The `inventory-store` KTable is exposed as a queryable state store. The `InventoryQueryController` REST endpoint allows any client to query the current inventory state directly from the Kafka Streams instance, without reading from Kafka topics. `GET /inventory` returns all detected blocks as a cubeId-to-color map. `GET /inventory/{cubeId}` returns the entry for a specific cube.

The controller uses `StoreQueryParameters.fromNameAndType` and `QueryableStoreTypes.keyValueStore()` to access the read-only key-value store at runtime.

== Windowed Operations (Week 10)

*Sliding window join:* The stream-stream join in `BlockColorTopology` uses `JoinWindows.ofTimeDifferenceAndGrace(Duration.ofSeconds(10), Duration.ofSeconds(1))`. This is a sliding window over event time, allowing block and colour events that arrive within 10 seconds of each other to be joined. Unlike tumbling or hopping windows, a sliding window considers every possible time interval of the given size, making it well-suited for joining two streams that are not aligned to a fixed schedule.

*Wall-clock inactivity window (custom processor):* Block detection in `BlockColorTopology` relies on a custom `BlockInactivityProcessor`. A wall-clock punctuation fires every 200 ms and emits a `BlockDetectedEvent` when a sensor key has been quiet for 3 seconds. This implements session-window semantics driven by wall-clock time rather than stream time, which is necessary because physical blocks create a continuous stream of distance readings with no natural end marker. A standard Kafka Streams session window was not used because it advances only when new records arrive (see ADR 0012).

*Rising-edge aggregation:* `MoveBlockTopology` and `PickUpBlockTopology` use a stateful `aggregate` with a 2-second gap threshold to detect the first reading of a new block. This mirrors a session-window boundary condition: after a period of inactivity exceeding the gap threshold, the next record is treated as the start of a new session and triggers exactly one command.

Tumbling and hopping windows are not used in the current implementation. The use cases in KAFKEA (block detection and colour join) do not require fixed-interval aggregation, making sliding and session-style windows more appropriate. See the Reflections section for a discussion of where a tumbling window could be added as an additional analytical step.

== Serialization

All events are serialized and deserialized using a custom `JsonSerde<T>` built on Jackson. This keeps the setup self-contained without requiring a schema registry.

= Topology Descriptions

== BlockColorTopology

#figure(
  image("../images/kafka-streaming-topology-BlockColorTopology.png", width: 100%),
  caption: [BlockColorTopology: block detection and colour classification]
)

`BlockColorTopology` is the most complex of the three topologies. It detects block presence on the conveyor (distance branch), detects when a block has passed (inactivity processor), classifies the block's colour (colour branch), joins the two observations to produce a `BlockColorEvent`, and maintains a deduplicated inventory of all detected blocks.

The topology reads from two source topics: `sensor.distance.raw.v1` (continuous distance readings from the left sensor) and `sensor.color.raw.v1` (continuous RGB readings from the colour sensor). Both streams are filtered and rekeyed, then joined on the common key `"sliding-window-join"` within a 10-second sliding window. The join output is reduced per `cubeId` to keep only the first colour reading per block, ensuring idempotent inventory updates. The final result is published to `inventory.blocks.v1` and stored in the `inventory-store` KTable.

Additionally, every raw distance reading that indicates a block is present is forwarded to `sensor.block-present.v1`, where it is consumed by `MoveBlockTopology`.

*Processing steps:*

Distance branch:
+ Source `sensor.distance.raw.v1` → `KStream<String, DistanceEvent>`.
+ Filter: `distance < 25.0` cm → block is present.
+ SelectKey → `"distance-sensor"` (fixed key for consistent partitioning).
+ Publish block-present readings to `sensor.block-present.v1` (consumed by `MoveBlockTopology`).
+ Custom `BlockInactivityProcessor` backed by the `block-activity-store` KV state store: records the last-seen wall-clock timestamp per key. A wall-clock punctuation fires every 200 ms and emits a `BlockDetectedEvent(cubeId=UUID, timestamp)` when the key has been quiet for at least 3 seconds.
+ SelectKey → `"sliding-window-join"` + explicit repartition (ensures join tasks see matching keys).

Colour branch:
+ Source `sensor.color.raw.v1` → `KStream<String, ColorEvent>`.
+ MapValues: classify `(r, g, b)` → `BlockColor` enum (RED / GREEN / BLUE / YELLOW, or UNKNOWN if below brightness threshold).
+ Filter: discard UNKNOWN readings.
+ SelectKey → `"sliding-window-join"` + explicit repartition.
+ Publish classified colour to `color.classified.v1`.

Join and materialisation:
+ Stream-stream sliding-window join (10 s window, 1 s grace) → `BlockColorEvent(cubeId, color, timestamp)`.
+ SelectKey → `cubeId` + groupByKey + `reduce(first)` materialised as KTable `"inventory-store"`: keeps only the first confirmed colour per cube, ensuring idempotent inventory entries regardless of duplicate join outputs.
+ `toStream` → publish to `inventory.blocks.v1`.

*Implementation state:* Fully implemented. The colour classification thresholds in `BlockColor.from()` are heuristic constants and may require calibration for specific sensor hardware or lighting conditions.

*Justification:* The wall-clock inactivity processor was chosen over a session window because Kafka Streams session windows advance only with new records which could take a significant amount of time in a low-traffic or test environment like KAFKEA restocking. Wall-clock punctuation ensures block detection fires even when the sensor stream stops.

The sliding window join was chosen over a table join because colour events are continuous and not keyed to a specific block identity. Temporal proximity is the only way to associate a colour reading with a block.

#figure(
  image("../images/kafka-streaming-topology-BlockColorTopologyTimeline.png", width: 100%),
  caption: [BlockColorTopology: event timeline]
)

== MoveBlockTopology

#figure(
  image("../images/kafka-streaming-topology-MoveBlockTopology.png", width: 60%),
  caption: [MoveBlockTopology: conveyor stop trigger]
)

`MoveBlockTopology` stops the conveyor belt when a block arrives at the left sensor. It reads from `sensor.block-present.v1` (pre-filtered readings published by `BlockColorTopology`) and applies rising-edge detection via a stateful `aggregate`: a `ConveyorCommandEvent("STOP")` is emitted exactly once per block arrival, defined as the first reading after a 2-second absence gap.

*Processing steps:*
+ Source `sensor.block-present.v1` → `KStream<String, DistanceEvent>` (already keyed to `"distance-sensor"` by `BlockColorTopology`).
+ GroupByKey + `aggregate` → KTable `"move-block-edge-store"` of `BlockPresenceState(lastSeenTimestamp, risingEdge, edgeTimestamp)`. A rising edge is flagged when `currentTimestamp − lastSeenTimestamp > 2 s`.
+ `toStream` + filter: keep only states where `risingEdge == true`.
+ MapValues → `BlockMoveTriggerEvent(UUID, edgeTimestamp)`.
+ MapValues → `ConveyorCommandEvent("STOP", triggerId, timestamp)`.
+ Publish to `control.conveyor.commands.v1`.

*Implementation state:* Fully implemented.

*Justification:* Consuming from `sensor.block-present.v1` rather than re-reading the raw distance topic avoids duplicating the filter logic and keeps the topology simple. The rising-edge aggregation prevents a flood of stop commands from a single block that lingers in front of the sensor.

#figure(
  image("../images/kafka-streaming-topology-MoveBlockTopologyTimeline.png", width: 100%),
  caption: [MoveBlockTopology: event timeline]
)

== PickUpBlockTopology

#text(fill: red)[_Diagram pending — to be added before submission._]

`PickUpBlockTopology` commands the robot arm to pick up and place a block when it arrives at the right sensor. It reads raw distance from `sensor.distance.right.raw.v1`, applies the same `distance < 25.0` filter and rising-edge detection (2-second gap), and emits a `RobotArmCommandEvent("PICK_AND_PLACE")` to `control.robot-arm.commands.v1`.

This topology mirrors the structure of `MoveBlockTopology` but operates on a separate physical sensor and a different output channel (robot arm vs. conveyor). The rising-edge logic is intentionally duplicated rather than shared to keep each topology independently deployable and testable.

*Processing steps:*
+ Source `sensor.distance.right.raw.v1` → `KStream<String, DistanceEvent>`.
+ Filter: `distance < 25.0` cm → block is present at the right sensor.
+ SelectKey → `"distance-sensor-right"`.
+ GroupByKey + `aggregate` → KTable `"pick-up-block-edge-store"` of `BlockPresenceState(lastSeenTimestamp, risingEdge, edgeTimestamp)`. Rising edge fires when `currentTimestamp − lastSeenTimestamp > 2 s`.
+ `toStream` + filter: keep only states where `risingEdge == true`.
+ MapValues → `BlockPickUpTriggerEvent(UUID, edgeTimestamp)`.
+ MapValues → `RobotArmCommandEvent("PICK_AND_PLACE", triggerId, timestamp)`.
+ Publish to `control.robot-arm.commands.v1`.

*Implementation state:* Fully implemented. In the KAFKEA system the robot arm is also driven by the Factory service's Operaton BPMN process for order fulfilment. The Kafka Streams path provides an independent, sensor-driven pick-and-place trigger specifically for the restocking workflow.

= ADRs

The following ADRs are related to this assignment:

- ADR 0011: Rising-Edge Detection for Sensor Triggers.
- ADR 0012: Wall-Clock Punctuation for Block Detection.
- ADR 0013: JSON Serialization over Avro.


= Reflections

== What went well

The three-topology decomposition made it straightforward to reason about, test, and evolve each stream independently. `BlockColorTopology` handles block identity and colour classification. `MoveBlockTopology` and `PickUpBlockTopology` consume pre-processed events and apply simple rising-edge logic. The separation of concerns meant changes to inactivity detection (for example, adjusting the 3-second gap) had no impact on the conveyor or robot-arm topologies.

Materialising the inventory as a KTable with `reduce(first)` gave us idempotent inventory updates without any additional deduplication step. Kafka's at-least-once delivery combined with the first-wins reduction means that duplicate join outputs (which are expected with sliding windows) do not corrupt the inventory state.

The simulator made end-to-end testing possible without physical hardware. Being able to replay synthetic sensor sequences locally significantly reduced iteration time when tuning the inactivity and rising-edge thresholds.

== Challenges

The wall-clock punctuation in `BlockColorTopology` required stepping outside the Kafka Streams DSL and manually managing a state store, making the implementation more verbose than a DSL session window would have been. It was also necessary to be careful about the order of state store registration and topology wiring to avoid startup errors.

Getting the sliding-window join to produce correct results required explicit repartitioning of both input streams before the join. Without it, records with the same logical key could land on different tasks and never be joined. This behaviour is not immediately obvious from the Kafka Streams documentation.

The RGB colour classification thresholds are heuristic and sensitive to ambient light. Calibrating them against real sensor readings required iterating with the physical hardware. The simulator uses ideal values that do not fully reflect real lighting conditions.

== What we would improve

*Avro serialisation.* The current `JsonSerde<T>` backed by Jackson is self-contained but provides no schema evolution guarantees. Replacing it with Avro and a schema registry would enforce compatibility between producers and consumers and reduce payload size on the wire.

*Explicit windowed aggregation.* The windowed operations in this assignment are covered by the sliding-window join and the rising-edge aggregate. Adding an explicit tumbling or hopping window aggregation (for example, counting blocks per colour per minute for restocking analytics) would more directly illustrate the windowed-operations pattern from the lecture.

*Integration tests.* No `TopologyTestDriver` tests exist for any of the three topologies. Adding unit-level topology tests would make regressions immediately visible without needing to run a full Kafka stack.

*Configurable colour thresholds.* The RGB classification thresholds in `BlockColor.from()` are currently hardcoded constants. Externalising them into `application.yml` would simplify calibration for different lighting conditions or sensor hardware without requiring a recompile.

#pagebreak()

= Repository

Source code: #link("https://github.com/ielpo/edpo-project-group1")[github.com/ielpo/edpo-project-group1]

The `kafka-streams` service is located at `services/kafka-streams/`. A release tag for Assignment 2 will be added at submission time.

#pagebreak()

= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Building topologies, Validation against lecture content, Documentation, ADRs, Presentation],
  [Eva], [Building topologies, Topology implementation, Presentation],
  [Gianluca], [Building topologies, Simulator, Presentation],
)
