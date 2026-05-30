## Why

The kafka-streams service already implements the core Assignment 2 processing flow described in the report and ADRs, but the repository is not internally consistent about that fact. The current code, README, and exercise material reflect different generations of the design, which makes it unclear what is actually required, what is implemented, and what still needs to be brought to submission quality.

## What Changes

- Add a design document that compares the kafka-streams implementation against Assignment 2, the relevant Exercise 5 system context, and ADRs 0011-0013.
- Identify and document concrete gaps between required behavior and the current codebase, including documentation drift, topic/config mismatches, and missing validation coverage.
- Define follow-up implementation work needed to align the service and repository artifacts with the exercised and documented behavior.

## Capabilities

### New Capabilities
- `kafka-streams-exercise-alignment`: Define how the repository documents and verifies alignment between the kafka-streams implementation, Assignment 2 expectations, Exercise 5 integration context, and the accepted stream-processing ADRs.

### Modified Capabilities
- None.

## Impact

Affected areas include the kafka-streams service documentation, topology and domain comments, topic/config declarations, and the missing test surface for stream-processing behavior. The change also adds OpenSpec artifacts that can drive the remediation work.