## 1. Documentation Alignment

- [ ] 1.1 Update `services/kafka-streams/README.md` so it describes the implemented wall-clock inactivity processor, the left and right sensor topologies, the sliding-window color join, the inventory query endpoints, and the actual topic set.
- [ ] 1.2 Replace stale session-window, suppress, operator-button, and topic-key comments in the kafka-streams source files with descriptions that match the current implementation.

## 2. Topic Contract Cleanup

- [ ] 2.1 Decide whether `sensor.block-detected.v1` is a supported or internal topic and document that decision consistently in the service docs and code comments.
- [ ] 2.2 Move `color.classified.v1` into `application.yml` and `KafkaTopicConfig`, or remove the publication if it is not required, so published topics are no longer hardcoded and undocumented.

## 3. Regression Validation

- [ ] 3.1 Add `TopologyTestDriver` coverage for `BlockColorTopology` that verifies wall-clock inactivity detection and first-win inventory materialization.
- [ ] 3.2 Add `TopologyTestDriver` coverage for `MoveBlockTopology` and `PickUpBlockTopology` that verifies 2 second rising-edge gating and suppresses duplicate triggers from continuous readings.
- [ ] 3.3 Run the kafka-streams Maven test suite and confirm the documented Assignment 2 and ADR-driven behavior is covered by automated checks.