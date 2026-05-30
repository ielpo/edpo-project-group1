## Context

Assignment 2 introduces a dedicated kafka-streams service for restocking: it consumes left and right distance sensor events plus color readings, detects blocks, classifies colors, publishes conveyor and robot-arm commands, and exposes the materialized inventory through interactive queries. Exercise 5 provides the surrounding system context in which Order orchestrates, Factory executes, and Inventory remains the source of reservation state; the kafka-streams service is an additive restocking path rather than a replacement for that saga-based flow.

The current implementation in `services/kafka-streams` already matches the accepted ADRs on the core processing path:

- ADR 0011 is implemented by `MoveBlockTopology` and `PickUpBlockTopology` via a 2 second rising-edge aggregate.
- ADR 0012 is implemented by `BlockColorTopology` through a custom wall-clock punctuation processor with a 3 second inactivity gap and 200 ms punctuation interval.
- ADR 0013 is implemented through the custom `JsonSerde<T>` backed by Jackson.
- Assignment 2 features such as the left-sensor block detection flow, the right-sensor pick-up flow, the sliding-window color join, and the queryable `inventory-store` are present in code.

The main gap is not missing stream logic. The gap is that repository artifacts describe different versions of the topology and leave some runtime contracts implicit. The most important mismatches are:

- The service README still describes a session window plus `Suppress`, which conflicts with ADR 0012 and the current processor implementation.
- Topology comments still describe the older session-window design and stale topic/key assumptions.
- `BlockDetectedEvent` still documents an operator-button origin and a `cubeId` topic key, while the current topology emits the record from inactivity detection and forwards it on the join key.
- The code publishes `sensor.block-detected.v1` and `color.classified.v1`, but Assignment 2 primarily documents `sensor.block-present.v1`; `color.classified.v1` is also hardcoded instead of being declared in configuration and topic creation.
- There are no `TopologyTestDriver` or equivalent tests, despite the exercise report explicitly identifying missing topology tests as a weakness.

## Goals / Non-Goals

**Goals:**

- Produce an authoritative gap assessment between the kafka-streams implementation, Assignment 2 report, Exercise 5 context, and ADRs 0011-0013.
- Treat the current code as the source of truth for implemented behavior, then align documentation and repository contracts around it.
- Make topic ownership and topic stability explicit, especially for intermediate or observability-only outputs.
- Define the minimum automated test surface required to support the documented behavior.

**Non-Goals:**

- Redesign the stream-processing algorithms that already satisfy the Assignment 2 behavior.
- Replace JSON serialization with Avro or introduce a schema registry.
- Rework Exercise 5 orchestration, compensation, or human-intervention flows.
- Retune sensor thresholds or physical timing constants without new hardware evidence.

## Decisions

### Decision: Treat the implemented topologies as functionally complete for Assignment 2

The design treats the existing three-topology structure as the baseline implementation because the code already realizes the behaviors described by the assignment and ADRs: wall-clock block detection, sliding-window enrichment, rising-edge command triggering, and interactive inventory queries.

Alternative considered: declare the service incomplete because older documentation still mentions the superseded session-window design.

Why rejected: the runtime code, configuration, and topic flow show that the implemented behavior has moved beyond that older design; the problem is alignment, not missing topology logic.

### Decision: Make documentation drift a first-class remediation target

The first remediation slice should update the README, source comments, and domain comments so they describe the wall-clock processor, the right-sensor topology, and the current topic flow accurately.

Alternative considered: prioritize only executable tests and ignore documentation drift.

Why rejected: the current mismatch is large enough that reviewers can reasonably misread the service as still using the old session-window design, which undermines both grading and future maintenance.

### Decision: Explicitly classify published topics as stable outputs or internal/diagnostic streams

The service currently publishes more than the Assignment 2 topic table foregrounds. `sensor.block-present.v1` is a documented internal topic, `inventory.blocks.v1` and the command topics are stable outputs, while `sensor.block-detected.v1` and `color.classified.v1` need an explicit decision: either document them as internal/diagnostic and configure them consistently, or remove them if they are no longer needed.

Alternative considered: leave the extra topics implicit because they do not block the main flow.

Why rejected: implicit topic contracts create the highest risk of future accidental dependencies, especially when one of the topics is hardcoded and not declared alongside the others.

### Decision: Add topology-level regression tests instead of relying on report prose

The missing validation should be closed with `TopologyTestDriver` coverage for the processor and aggregate semantics that the ADRs depend on.

Alternative considered: rely on manual simulator runs and the report narrative.

Why rejected: the gap analysis identified behavior that is subtle and timing-sensitive. Simulator-only validation is too weak for wall-clock punctuation, rising-edge detection, and first-win inventory materialization.

### Decision: Preserve the Exercise 5 boundary as context, not as a change target

Exercise 5 remains relevant because it defines the surrounding Order, Inventory, Factory, and Dashboard landscape. This change uses that context only to verify that kafka-streams remains an additive restocking service and does not silently change the saga-oriented system contracts.

Alternative considered: extend this change into order/factory workflow redesign.

Why rejected: that would dilute the change and expand beyond the repository area the user asked to analyze.

## Risks / Trade-offs

- [A topic cleanup may affect undocumented consumers] -> Mitigation: audit downstream references before removing or renaming `sensor.block-detected.v1` or `color.classified.v1`; prefer documenting and configuring them first.
- [Topology tests for punctuation can be brittle if they depend on wall-clock timing incorrectly] -> Mitigation: use `TopologyTestDriver` time controls and isolate the processor behavior with deterministic timestamps.
- [Documentation-first alignment can leave runtime inconsistencies temporarily visible] -> Mitigation: pair docs updates with a small config/comment cleanup in the same implementation slice.
- [Treating current code as the baseline may preserve accidental behavior] -> Mitigation: require explicit decisions for every currently published but weakly documented topic before calling the change complete.

## Migration Plan

1. Update repository documentation and stale source comments to reflect the actual topology and ADR-backed behavior.
2. Decide the intended contract for `sensor.block-detected.v1` and `color.classified.v1`.
3. Either declare those topics in configuration and topic provisioning or remove the publications if they are unnecessary.
4. Add topology tests that cover inactivity detection, rising-edge detection, and first-write inventory materialization.
5. Validate with OpenSpec status and the kafka-streams Maven test suite.

Rollback is straightforward for the documentation and test work. If topic cleanup is performed, rollback should retain or restore previous publications until all consumers are known.

## Open Questions

- Is `sensor.block-detected.v1` intended to be a supported runtime contract, or is it only a leftover/internal diagnostic stream?
- Is `color.classified.v1` required for observability, and if so should it be added to `application.yml` and `KafkaTopicConfig`?
- Are there any consumers outside this service that rely on the current key of `sensor.block-detected.v1` being `sliding-window-join` rather than `cubeId`?
- Should the Assignment 2 report be updated to mention the extra diagnostic topic(s), or should the implementation be simplified to match the documented topic set exactly?