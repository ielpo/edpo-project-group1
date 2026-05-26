# 12. Wall-Clock Punctuation for Block Detection

Date: 2026-05-10

## Status

Accepted

## Context

Block detection requires emitting an event once a block has fully passed the sensor, i.e. after a period of inactivity. Kafka Streams session windows and the `Suppress` API both rely on stream time advancing, which only happens when new records arrive. In a low-traffic or test environment the sensor stream may pause entirely, meaning a session never closes.

## Decision

Use a custom `BlockInactivityProcessor` with wall-clock punctuation (every 200 ms) instead of a session window. The processor emits a `BlockDetectedEvent` when a sensor key has been quiet for 3 seconds of wall-clock time.

## Consequences

- Block detection fires reliably even when the sensor stream is idle, which is essential for the simulator and for low-throughput scenarios.
- The punctuation fires at a fixed interval regardless of load, creating minor CPU overhead when the conveyor is idle.
- The implementation is more verbose than a session window and bypasses the Kafka Streams DSL, requiring manual state store management.
