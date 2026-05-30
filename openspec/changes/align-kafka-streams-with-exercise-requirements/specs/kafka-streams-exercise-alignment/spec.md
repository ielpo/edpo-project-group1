## ADDED Requirements

### Requirement: Kafka Streams exercise alignment design summary
The repository SHALL provide a design artifact for the kafka-streams service that compares implemented behavior against Assignment 2, the relevant Exercise 5 system context, and ADRs 0011, 0012, and 0013, and SHALL identify any remaining implementation or documentation gaps.

#### Scenario: Reviewer reads the change design
- **WHEN** a reviewer opens the change design artifact
- **THEN** the artifact describes which Assignment 2 and ADR behaviors are already implemented
- **AND** it lists the remaining gaps that must be closed for repository alignment

### Requirement: Kafka Streams documentation matches implemented topology behavior
The kafka-streams service documentation and topology comments SHALL describe the implemented wall-clock inactivity processor, the left and right sensor topologies, the sliding-window color join, the queryable inventory store, and the JSON serde approach. They SHALL NOT describe the superseded session-window plus suppress design as the current implementation.

#### Scenario: Maintainer reads repository documentation
- **WHEN** a maintainer reviews the kafka-streams README and topology comments
- **THEN** the documented processing flow matches the behavior implemented in code
- **AND** the maintainer is not told that session-window suppression is the active block-detection mechanism

### Requirement: Published topics are explicitly classified and configured
Every topic published by the kafka-streams service SHALL be either declared as a supported topic in configuration and topic provisioning or explicitly documented as an internal or diagnostic stream. Hardcoded published topic names SHALL NOT remain undocumented.

#### Scenario: Maintainer compares published topics with configuration
- **WHEN** a maintainer inspects the kafka-streams topology code, application configuration, and topic configuration
- **THEN** each published topic is either configured consistently or explicitly documented as internal
- **AND** no published topic is left as an unexplained hardcoded contract

### Requirement: Topology behavior is covered by automated regression tests
The kafka-streams service SHALL include automated topology tests that cover wall-clock inactivity block detection, 2 second rising-edge command triggering, and first-win inventory materialization using the JSON serdes.

#### Scenario: Test suite validates exercise-critical behavior
- **WHEN** the kafka-streams test suite is executed
- **THEN** it verifies block detection after inactivity without relying on new stream records
- **AND** it verifies that repeated sensor readings within the inactivity gap do not emit duplicate command triggers
- **AND** it verifies that duplicate join outputs do not overwrite the first stored block color for a cube