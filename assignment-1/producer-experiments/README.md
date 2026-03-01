# Assignment1

## Overview

This experiment consists of a single part.

We test batch sizes and the impact on processing latency.

## Running the Docker image

1. Open a terminal in the directory: docker/.
2. Start the Kafka process using Docker Compose:

    ```
    $ docker compose up
    ```

## Quick Batch-Size Experiment (3 variants)

- Producer: [BatchSizeExperimentProducer](ClickStream-Producer/src/main/java/com/examples/BatchSizeExperimentProducer.java)
- Consumer: [BatchSizeLatencyConsumer](consumer/src/main/java/com/examples/BatchSizeLatencyConsumer.java)
- Variants (topics recreated by the producer):
  - clicks-batch-16k: batch.size=16KB, linger.ms=5
  - clicks-batch-64k: batch.size=64KB, linger.ms=15
  - clicks-batch-128k: batch.size=128KB, linger.ms=30
- Using topic suffixes is recommended as deleting topics is asynchronous; topics are `clicks-batch-16k-<runId>`, `clicks-batch-64k-<runId>`, `clicks-batch-128k-<runId>`.
- Flow:
  2) Run consumer with that runId (waits, reports latencies when each topic hits target):
  1) Run producer (generates a runId, creates the topics, sends msgs):
  3) Consumer prints min/p50/p95/p99/avg per topic and exits. If you want a shorter run, lower `targetPerTopic`.
- Manual topic cleanup is required when reusing topics; If you want to delete old topics manually, you can use `kafka-topics --delete` inside the broker container as needed.
- To test linger.ms impact further, see comment in the producer code










