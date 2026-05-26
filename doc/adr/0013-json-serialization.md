# 13. JSON Serialization over Avro

Date: 2026-05-26

## Status

Accepted

## Context

Kafka Streams requires a serialization format for all topics it reads and writes. Avro with a schema registry provides schema evolution guarantees and a compact binary wire format, but requires running and operating a schema registry alongside the Kafka broker.

## Decision

Use a custom `JsonSerde<T>` backed by Jackson for all stream processing topics. No schema registry is deployed.

## Consequences

- The setup remains self-contained: no additional infrastructure is required beyond the Kafka broker.
- Schema evolution is not enforced, producers and consumers must be updated in sync to avoid deserialization failures.
- JSON payloads are larger than Avro binary, which is acceptable for the data volumes produced in this project.
