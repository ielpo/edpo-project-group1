## Purpose

Preserve the simulator service contract while ensuring simulator-origin events are delivered without blocking state progression.

## Requirements

## MODIFIED Requirements

### Requirement: Event bridge modes
The service MUST support `SIMULATOR_EVENT_BRIDGE` values `kafka`, `http`, and `none`, and MUST route simulator-origin events according to the selected mode. Bridge delivery MUST be scheduled asynchronously so slow external callbacks do not block simulation state progression.

#### Scenario: HTTP bridge is enabled
- **WHEN** `SIMULATOR_EVENT_BRIDGE=http`
- **AND** the configured HTTP callback target responds slowly
- **THEN** simulator-origin events are still queued for delivery asynchronously
- **AND** the simulation loop continues advancing state
- **AND** the same event remains in the local event history