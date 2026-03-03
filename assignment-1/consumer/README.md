# Consumer Lag & Data Loss Risks — Experiment

This module demonstrates three distinct Kafka consumer behaviours:

| Scenario | Behaviour |
|---|---|
| A — Baseline | Consumer keeps up; lag ≈ 0 |
| B — Moderate lag | Slow processing causes lag to grow steadily |
| C — Rebalance trigger | Processing too slow between polls; Kafka removes the consumer, triggers rebalance, re-delivers uncommitted messages → duplicate records |

---

## Step 1 — Start Kafka

From the repo root:

```bash
docker compose up
```

Kafka will be available at `localhost:9092`. Keep this terminal open.

---

## Step 2 — Start the Eye-Tracker Producer

Run the application _com.examples.EyeTrackersProducer_ in `consumer-experiments-producer`.
This produces ~125 gaze events/sec across 2 partitions of the `gaze-events` topic.

---

## Step 3 — Run LagMonitor (keep running for all scenarios)

Build the `consumer-experiments-consumer` module and execute _com.experiments.LagMonitor_

It polls Kafka's AdminClient every 2 seconds and prints:

```
[12:00:01] partition=0  | committed=   142 | logEnd=   260 | lag=   118
[12:00:01] partition=1  | committed=   139 | logEnd=   258 | lag=   119
```

Leave this running throughout all three scenarios.

---

## Step 5 — Run the Scenarios

Open `SlowConsumer.java` and change the two constants at the top of the class before each run.

### Scenario A — Baseline (no lag)

```java
private static final String PROPERTIES_FILE     = "consumer-baseline.properties";
private static final long   PROCESSING_DELAY_MS = 0;
```

**What to observe:**
- LagMonitor shows lag ≈ 0 for both partitions.
- SlowConsumer prints records as fast as they arrive.

---

### Scenario B — Moderate lag

```java
private static final String PROPERTIES_FILE     = "consumer-baseline.properties";
private static final long   PROCESSING_DELAY_MS = 200;
```

**What to observe:**
- Each record takes 200 ms to process; the consumer handles ~5 records/sec.
- The producer emits ~125 records/sec, so lag grows at ~120 records/sec.
- LagMonitor shows steadily increasing lag values across both partitions.

---

### Scenario C — Rebalance trigger (duplicate records)

```java
private static final String PROPERTIES_FILE     = "consumer-low-maxpoll.properties";
private static final long   PROCESSING_DELAY_MS = 8000;
```

`consumer-low-maxpoll.properties` sets `max.poll.interval.ms=5000` and `max.poll.records=1`.
With `max.poll.records=1` the consumer fetches exactly one record per poll, then sleeps 8 000 ms
to simulate processing. The total time between two `poll()` calls is therefore ~8 000 ms,
which comfortably exceeds the 5 000 ms limit and reliably triggers a rebalance every cycle.

**What to observe:**
- Kafka logs show:
  ```
  Revoked partitions: [gaze-events-0, gaze-events-1]
  Assigned partitions: [gaze-events-0, gaze-events-1]
  ```
- LagMonitor shows lag spikes as the committed offset resets.
- SlowConsumer output contains **duplicate `eventID` values** — Kafka re-delivered uncommitted messages after the rebalance.

---

## Configuration Files

| File | Purpose                                                                                 |
|---|-----------------------------------------------------------------------------------------|
| `consumer-baseline.properties` | Default settings; `max.poll.interval.ms` is 300,000 ms (5 min)                          |
| `consumer-low-maxpoll.properties` | Sets `max.poll.interval.ms=5000` and `max.poll.records=1` to reliably trigger rebalance |

---

## Key Concepts Demonstrated

**Consumer Lag** — the difference between the log-end offset (latest produced) and the committed offset (latest processed). Grows when processing is slower than production.

**max.poll.interval.ms** — the maximum time Kafka allows between two consecutive `poll()` calls. If exceeded, the broker treats the consumer as dead, removes it from the group, and triggers a rebalance.

**Rebalance + Duplicate Delivery** — after a rebalance, partitions are reassigned and Kafka re-delivers all records from the last *committed* offset. If the consumer was slow to commit, some records are delivered twice — a form of data duplication risk.
