#set document(
  title: "Exercise 1: Kafka - Getting Started\nExercise 2: Kafka with Spring",
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
  Deadline: 03.03.2026; 23:59 \
  Group 1, Team Members: \
  Michael Schütz, Gianluca Ielpo, Eva Amromin
]

#outline()
#pagebreak()

= Experiments with Kafka <exercise-1-experiments-with-kafka>

The code for these experiments is available at
#link("https://github.com/ielpo/edpo-project-group1/tree/main/exercise-1")[github.com/ielpo/edpo-project-group1/exercise-1]

== Producer Experiments <producer-experiments>

#link("https://github.com/ielpo/edpo-project-group1/tree/main/exercise-1/producer-experiments")[github.com/ielpo/edpo-project-group1/exercise-1/producer-experiments]

=== Batch Size & Processing Latency (no artificial delay) <batch-size-processing-latency-no-artificial-delay>

This experiment discusses the impact of Kafka producer batch size (#emph[batch.size];) and linger time (#emph[linger.ms];) on throughput and end-to-end latency.

Batch size controls how much data is accumulated before sending, while linger time defines how long the producer waits to allow additional records to join a batch before dispatching it.

Six experiments were conducted using three batch sizes (16 KB, 64 KB, 128 KB) using two linger settings (5 ms and 100 ms). For each
configuration, 100'000 messages were produced and measured for throughput and latency. \
Results are presented as averages and reflect a small sample size of three runs per configuration.

==== Results: linger.ms = 5 ms (Default) <results-linger.ms-5-ms-default>

#strong[Producer Throughput (Average of three runs)]
#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto, auto),
    table.header([#strong[Batch Size];], [#strong[Throughput (messages/s)];]),
    table.hline(),
    [16 KB], [\~ 131'000],
    [64 KB], [\~ 255'000],
    [128 KB], [\~ 393'000],
  )],
  kind: table,
)

Throughput increased consistently with larger batch sizes, despite using the default linger value (#link("https://kafka.apache.org/41/configuration/producer-configs/#:~:text=This%20linger.ms%20setting%20defaults,linger%20time%20than%20this%20setting.")[kafka.apache.org];).

#strong[Consumer Latency (Average of three runs)]

#figure(
  align(center)[#table(
    columns: (33.33%, 33.33%, 33.33%),
    align: (auto, auto, auto),
    table.header([#strong[Batch Size];], [#strong[p50 (ms)];], [#strong[Average Latency (];#strong[ms)];]),
    table.hline(),
    [16 KB], [\~ 1004], [\~ 886],
    [64 KB], [\~ 599], [\~ 564],
    [128 KB], [\~ 351], [\~ 387],
  )],
  kind: table,
)

Larger batch sizes reduced both the median and the mean latency. Although larger batches theoretically introduce additional waiting time, the tested high-throughput workload saw batches fill up almost immediately. Consequently, the reduction in network and broker overhead appears to have offset any additional delay caused by batching, resulting in lower overall end-to-end latency.

This observation matches the description of linger time in the documentation (#link("https://kafka.apache.org/41/configuration/producer-configs/#:~:text=This%20linger.ms%20setting%20defaults,linger%20time%20than%20this%20setting.")[kafka.apache.org];).

==== Results: linger.ms = 100 ms <results-linger.ms-100-ms>

#strong[Producer Throughput (Average of three runs)]

#figure(
  align(center)[#table(
    columns: (auto, auto),
    align: (auto, auto),
    table.header([#strong[Batch Size];], [#strong[Average Throughput (messages/s)];]),
    table.hline(),
    [16 KB], [\~ 122'000],
    [64 KB], [\~ 231'000],
    [128 KB], [\~ 393'000],
  )],
  kind: table,
)

Using the 100 ms configuration, throughput increased as the batch size increased. However, when comparing the 5 ms and 100 ms settings, increasing the linger time did not have a significant impact on throughput. This suggests that the batches were already filling up quickly due to the high message rate.

#strong[Consumer Latency (Average of three runs)]

#figure(
  align(center)[#table(
    columns: (auto, auto, auto),
    align: (auto, auto, auto),
    table.header([#strong[Batch Size];], [#strong[p50 (ms)];], [#strong[Average Latency (ms)];]),
    table.hline(),
    [16 KB], [\~ 926], [\~ 820],
    [64 KB], [\~ 436], [\~ 393],
    [128 KB], [\~ 431], [\~ 595\*],
  )],
  kind: table,
)

Median latency decreased from 16 KB to 64 KB but did not further improve at 128 KB. The higher mean is due to an outlier in the first run of the experiment; without this outlier, the latency would be lower than with the 64 KB batch size.

==== Interpretation <interpretation>

Variance between individual runs was noticeable and is likely attributable to JVM warm-up effects, operating system scheduling, and broker-side processing variability. The missing warm-up phase may slightly influence absolute early-message latency. However, since all configurations were tested identically, the relative trends should remain valid.

Given the small sample size of three runs per configuration, the results should be interpreted with caution.

Throughput was found to increase as batch size was increased across all experiments, as was explained in the lecture. Increasing linger time did not significantly affect throughput under this workload. Messages were produced continuously at high speed, so batches filled almost immediately and the linger timer had little impact on batch size.

=== Batch Size & Processing Latency (with artificial delay) <batch-size-processing-latency-with-artificial-delay>

An additional experiment introduced a small artificial delay of 0-2 ms between produced messages. The goal was to slightly reduce the production rate and observe its effect on batching behaviour.

Due to the increased running time, this experiment was only conducted once.

==== Results: linger.ms = 5 ms (0--2 ms artificial delay) <results-linger.ms-5-ms-02-ms-artificial-delay>

#strong[Producer Throughput]

#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto, auto),
    table.header([#strong[Batch Size];], [#strong[Average Throughput (messages/s)];]),
    table.hline(),
    [16 KB], [\~ 1'697],
    [64 KB], [\~ 1'747],
    [128 KB], [\~ 1'769],
  )],
  kind: table,
)

With a small delay, throughput increased only marginally as batch size increased. The system was largely limited by the reduced message rate rather than by batching efficiency.

#strong[Consumer Latency]

#figure(
  align(center)[#table(
    columns: (auto, auto, auto),
    align: (auto, auto, auto),
    table.header([#strong[Batch Size];], [#strong[p50 (ms)];], [#strong[Average Latency (ms)];]),
    table.hline(),
    [16 KB], [\~ 4], [\~ 4.60],
    [64 KB], [\~ 4], [\~ 4.25],
    [128 KB], [\~ 4], [\~ 4.25],
  )],
  kind: table,
)

Median latency remained constant across configurations. Larger batches slightly reduced average but the differences were not significant.

==== Results: linger.ms = 100 ms (0--2 ms artificial delay) <results-linger.ms-100-ms-02-ms-artificial-delay>

#strong[Producer Throughput]

#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto, auto),
    table.header([#strong[Batch Size];], [#strong[Average Throughput (messages/s)];]),
    table.hline(),
    [16 KB], [\~ 910],
    [64 KB], [\~ 1'158],
    [128 KB], [\~ 1'131],
  )],
  kind: table,
)

With a higher linger time, throughput decreased significantly compared to the 5 ms configuration. Larger batches had no significant impact.

#strong[Consumer Latency]

#figure(
  align(center)[#table(
    columns: (auto, auto, auto),
    align: (auto, auto, auto),
    table.header([#strong[Batch Size];], [#strong[p50 (ms)];], [#strong[Average Latency (ms)];]),
    table.hline(),
    [16 KB], [\~ 60], [\~ 58.67],
    [64 KB], [\~ 59], [\~ 57.94],
    [128 KB], [\~ 59], [\~ 57.72],
  )],
  kind: table,
)

Median latency increased substantially and came surprisingly close to the configured 100 ms linger time. Batch size had minimal impact on median latency.

==== Interpretation <interpretation-1>

By slightly reducing the message rate, batches no longer filled immediately. As a result, linger.ms became the dominant factor. Instead of improving throughput, a higher linger introduced additional waiting time. Since the system runs locally with minimal network overhead, batching provided limited performance gains under these conditions.

=== Conclusion <conclusion>

For the project, linger time and batch size appear to be two promising parameters for performance tuning, particularly in high-throughput scenarios where batching efficiency significantly impacts overall system behaviour.

== Consumer Experiments <consumer-experiments>

#link("https://github.com/ielpo/edpo-project-group1/tree/main/exercise-1/consumer-experiments")[github.com/ielpo/edpo-project-group1/exercise-1/consumer-experiments]

=== Consumer Lag & Data Loss Risks <consumer-lag-data-loss-risks>

==== Setup <setup>

The experiment uses an EyeTrackers-Producer that emits approximately 125 gaze events per second across two partitions of the gaze-events topic. A SlowConsumer instance subscribes to the topic and introduces a configurable per-record processing delay. A LagMonitor utility that was written for this experiment polls the Kafka AdminClient every two seconds and prints the committed offset, log-end offset, and lag for each partition, allowing the effect of the delay to be observed in real time.

==== Scenario A - Baseline (no processing delay) <scenario-a---baseline-no-processing-delay>

With PROCESSING\_DELAY\_MS = 0 (SlowCosumer) and default consumer settings (max.poll.interval.ms = 300,000 ms), the consumer kept pace with the producer. LagMonitor consistently reported lag of 2--5 on partition 0 and 4--6 on partition 1 throughout the 120-second observation window. This confirms that, without artificial delay, a single consumer is sufficient to drain the gaze-events topic in near real time.

==== Scenario B --- Moderate Lag (200 ms per record) <scenario-b-moderate-lag-200-ms-per-record>
Setting PROCESSING\_DELAY\_MS = 200 reduced the consumer\'s throughput to approximately 5 records/second (one record every 200 ms) while the producer continued at \~125 records/second. The resulting net lag growth rate was \~120 records/second per partition. LagMonitor confirmed steady accumulation across both partitions, as shown in the table below. No rebalances occurred because the total time between poll() calls remained well below max.poll.interval.ms (300,000 ms).

#figure(
  align(center)[#table(
    columns: (auto, auto, auto),
    align: (auto, auto, auto),
    table.header([#strong[Time];], [#strong[Lag P0];], [#strong[Lag P1];]),
    table.hline(),
    [t = 10 s], [208], [241],
    [t = 30 s], [217], [251],
    [t = 60 s], [255], [283],
  )],
  kind: table,
)

==== Scenario C --- Rebalance Trigger & Duplicate Delivery <scenario-c-rebalance-trigger-duplicate-delivery>

Changing PROCESSING\_DELAY\_MS = 8,000 ms and switching to consumer maxpoll.properties (max.poll.interval.ms = 5,000 ms) caused the time between consecutive poll() calls to exceed the allowed interval. Kafka\'s broker detected the consumer as unresponsive and forcibly removed it from the consumer group, triggering a rebalance. The partitions were revoked and immediately re-assigned to the same consumer instance. Because the slow consumer had not committed the offsets of the records, it was still processing, Kafka re-delivered those records from the last committed position. This was directly observable in the SlowConsumer output: the same offset and eventID appeared multiple times in succession (shown below).
`
[SlowConsumer] partition=0 offset=3987 eventID=8169 x=1739 y=541 pupil=3
[SlowConsumer] partition=0 offset=3987 eventID=8169 x=1739 y=541 pupil=3
`

LagMonitor captured the following snapshot at peak lag immediately after the rebalance:
`
partition 0 - committed = 3987, log-end = 82892, lag = 78905
partition 1 - committed = 3641, log-end = 82994, lag = 79353
`

The committed offsets remained frozen at the pre-rebalance values while the log-end offsets continued advancing, explaining the sudden lag spike.

==== Scenario D --- Retention-Based Record Loss <scenario-d-retention-based-record-loss>

To demonstrate that unbounded lag eventually causes permanent data loss, the gaze-events topic was configured with a short retention policy before the run:
`
retention.ms = 15,000 ms (15 seconds)
segment.ms = 10,000 ms (10 seconds)
`

The segment.ms setting was required because Kafka deletes data at the segment level, not record by record. A segment must be closed before it becomes eligible for deletion. With the default segment size of 1 GB, retention would never trigger under normal load, so segment.ms = 10,000 was added to force segment rolls every 10 seconds. SlowConsumer was run with PROCESSING\_DELAY\_MS = 200, identical to Scenario B. LagMonitor was extended to also track logStartOffset---the earliest offset still available on the broker.

After approximately 630 seconds, LagMonitor reported:
`
[00:19:34] partition=0 | logStart= 37399 | committed= 7645 | logEnd= 38684 | lag= 3103 *** DATA LOSS: 29754 records deleted before consumer reached them ***
[00:19:34] partition=1 | logStart= 37279 | committed= 5103 | logEnd= 38560 | lag= 33457 *** DATA LOSS: 32176 records deleted before consumer reached them ***
`

logStartOffset jumped from 0 to 37,399 in a single step as Kafka deleted an entire segment. The consumer's committed offset was only 7,645, a gap of 29,754 records on partition 0 and 32,176 on partition 1 that were permanently lost before the consumer could reach them. This directly confirms the risk described in Scenario B: unchecked lag, combined with time-based retention, leads to silent and irrecoverable data loss.

==== Conclusion <conclusion-1>

The four scenarios demonstrate a clear progression of risk. When processing keeps pace with production (Scenario A), lag is negligible and consumer group membership is stable. When processing is slower than production (Scenario B), lag accumulates continuously. Scenario D directly demonstrates the consequence of unchecked lag: once the consumer falls far enough behind, Kafka's time-based retention permanently deletes unconsumed records before the consumer can reach them, as observed with 29,754 lost records on partition 0 and 32,176 on partition 1. The most severe outcome in terms of operational disruption occurs when per-record processing time exceeds max.poll.interval.ms (Scenario C): Kafka evicts the consumer, triggers a rebalance, and re-delivers uncommitted records, leading to duplicate processing. In production systems these risks are mitigated by keeping per-record processing time short (offloading slow work to separate threads), setting max.poll.interval.ms appropriately, tuning retention.ms with realistic worst-case lag in mind, and using idempotent consumers or exactly-once semantics where duplicate or missing delivery is unacceptable.

== Fault Tolerance and Reliability <fault-tolerance-and-reliability>

#link("https://github.com/ielpo/edpo-project-group1/tree/main/exercise-1/reliability-experiments")[github.com/ielpo/edpo-project-group1/exercise-1/reliability-experiments]

=== Fault Tolerance on Loss of Brokers <fault-tolerance-on-loss-of-brokers>

==== Setup <setup-1>
The Kafka cluster is composed of 3 brokers and 1 controller. A topic is created with one partition and a replication factor of two. The experiment aims at exploring the behaviour of the cluster under different failure scenarios.

`
acks=all
retries=2147483647 `(maximum value)`
delivery.timeout.ms=120000
request.timeout.ms=100000
retry.backoff.ms=500
metadata.max.age.ms=20000

KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 2
KAFKA_DEFAULT_REPLICATION_FACTOR: 2
KAFKA_MIN_INSYNC_REPLICAS: 2
`

==== Case 1 <case-1>
The leader of the topic is killed, simulating a broker going offline. The publishing and receiving of messages are observed.

After the leader is lost, the cluster automatically elects the follower as new leader and messages continue to be propagated. There is a short delay until the failover happens, the synchronous producer waits until the messages are delivered to the broker again. No data loss on acknowledged send.

==== Case 2 <case-2>
The follower of the topic is killed.

After the follower is lost, the cluster does not change configuration. The existing leader remains leader and continues to receive and forward messages without interruption. No data loss on acknowledged send.

==== Case 3 <case-3>
Both leader and follower are killed. Simulating a contemporary failure of two brokers.

After both assigned replicas are lost, the partition has no remaining in-sync replica, so Kafka cannot elect a new leader and the topic becomes unavailable. The third broker is not automatically added as a replacement replica, because replica placement is fixed unless explicitly reassigned by an admin operation. This is also due to data safety, as adding a new blank replica when no other replicas are available entails possibly breaking message ordering guarantees.

==== Results <results>
The failure of a single broker in a two-way redundant setup does not impact data integrity but can lead to short unavailability during the election of the new leader.

The failure of both brokers in a two-way redundant setup makes the topic unavailable to send or poll.

In both cases, the cluster does not assign the replication to a third free broker. This is by design and is a consequence of a trade-off between availability and consistency.

#pagebreak()

= Exercise 2: Software Project <exercise-2-software-project>

#link("https://github.com/ielpo/edpo-project-group1/tree/main")[github.com/ielpo/edpo-project-group1]

== Event-carried state transfer <event-carried-state-transfer>
=== Project Description <project-description>

The project is called #strong[KAFKEA], a blend of #emph[Kafka] and #emph[IKEA] (the version used here is simplified compared to the later exercises, see exercise 3). It implements an event-driven manufacturing scenario for custom furniture orders. \
A customer places an order through a web form selecting a furniture item and colour. The Order service orchestrates the end-to-end process: it reserves the required inventory, commands the Factory service to manufacture the item using a Dobot Magician robot arm, and waits for the outcome. A Dashboard service provides real-time visibility into the order lifecycle for all running flows.

=== Applied EDA Pattern: Event Notification and Event-Carried State Transfer <applied-eda-pattern-event-notification-and-event-carried-state-transfer>

The core idea of Event-Carried State Transfer is that events carry enough data for consumers to act locally, without ever calling back to the source of service. The system applies this pattern across its core services:

- #strong[Order Service:] publishes the `order.manufacture.v1` command carrying all data the Factory needs to start manufacturing. It subscribes to `order.complete.v1` and `error.v1` to continue or compensate the workflow without polling Factory.

- #strong[Factory Service:] subscribes to `order.manufacture.v1` and executes manufacturing. It publishes `order.complete.v1` carrying the completion state, and emits `info.v1` and `error.v1` events throughout the process.

- #strong[Dashboard Service:] subscribes to `info.v1` and `error.v1` and maintains a local view of all running flows and inventory state, entirely from the events it receives, without querying Order or Factory directly.

#pagebreak()
The table below shows each event and the state it carries:

#figure(
  align(center)[#table(
    columns: (auto, auto, auto, auto),
    align: (auto, auto, auto, auto),
    table.header([Topic], [Producer → Consumer], [State Transferred], [How It Is Used]),
    table.hline(),
    [order.manufacture.v1],
    [Order → Factory],
    [orderId, item, colour],
    [Factory starts manufacturing without querying Order for details.],
    [order.complete.v1],
    [Factory → Order, Dashboard],
    [orderId, result],
    [Order continues the workflow; Dashboard marks the order as complete.],
    [info.v1],
    [Order, Factory → Dashboard],
    [orderId, status message],
    [Dashboard displays real-time progress without polling any service.],
    [error.v1],
    [Order, Factory → Order, Dashboard],
    [orderId, error details],
    [Order triggers compensation; Dashboard displays the failure.],
  )],
  kind: table,
)

The Inventory service is intentionally excluded here: it is called synchronously over HTTP by the Order service to reserve stock. Since no state is transferred via events, it falls outside the scope of this pattern.

=== Why Not Synchronous Request/Response? <why-not-synchronous>

Without Event-Carried State Transfer, the Dashboard would need to continuously poll Order and Factory for status updates, and Order would need to poll Factory to detect when manufacturing is complete. This creates temporal coupling: if Factory is slow or unavailable, the Order process stalls and the Dashboard goes stale. By publishing events that carry state, each service acts independently on the information it receives. The trade-off is eventual consistency: the Dashboard may briefly lag behind the actual process state, which is acceptable for a status display.

#pagebreak()

= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Producer Experiments],
  [Eva], [Consumer Experiments, Software Project],
  [Gianluca], [Fault Tolerance Experiment],
)

