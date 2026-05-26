# 11. Rising-Edge Detection for Sensor Triggers

Date: 2026-05-10

## Status

Accepted

## Context

Distance sensors publish a continuous stream of readings while a block is in range, potentially at rates of hundreds of messages per second. The downstream consumers — conveyor controller and robot arm controller — expect exactly one command per block arrival. Forwarding every raw reading directly would either require consumers to implement their own deduplication, or result in repeated commands being sent to the physical hardware.

## Decision

Implement rising-edge detection in `MoveBlockTopology` and `PickUpBlockTopology` using a stateful KTable `aggregate`. A trigger event is emitted exactly once when the gap between the previous and current reading exceeds 2 seconds, indicating a new block has appeared after a period of absence. This keeps deduplication inside the stream processing layer and out of the hardware control services.

## Consequences

- Each downstream consumer receives exactly one command per block regardless of sensor rate or how long the block lingers in front of the sensor.
- The 2-second gap threshold couples the topology to the physical conveyor speed. If operating conditions change, the threshold must be updated.
- Two blocks arriving within 2 seconds of each other are treated as one arrival. This is acceptable given the physical constraints of the conveyor, where sub-2-second intervals are not achievable at normal operating speed.
