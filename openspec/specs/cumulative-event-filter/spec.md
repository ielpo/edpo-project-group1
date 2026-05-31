# Cumulative Event Filter

Version: v1

## Purpose
Provide cumulative per-type filtering in the event panel, allowing users to independently toggle visibility of each event type through a multi-select chip UI.

## Requirements

### Requirement: Cumulative type filter via query parameter
The events fragment endpoint SHALL accept a `filter` query parameter containing a comma-separated list of event type names (case-insensitive). The server SHALL normalize type names to uppercase and filter the event list to include only events whose type is in the specified set.

When the `filter` parameter is absent, the endpoint SHALL default to the process set: `KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`.

When the `filter` parameter is present but empty, the endpoint SHALL return no events.

Unrecognized type names in the parameter SHALL be silently ignored.

#### Scenario: Filter with specific types
- **WHEN** a client requests `/fragments/events?filter=kafka,state`
- **THEN** the response contains only events of type `KAFKA` and `STATE`
- **AND** events of other types are excluded

#### Scenario: Missing filter parameter defaults to process set
- **WHEN** a client requests `/fragments/events` without a `filter` parameter
- **THEN** the response contains only events of types `KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`

#### Scenario: Empty filter shows no events
- **WHEN** a client requests `/fragments/events?filter=`
- **THEN** the response contains no events
- **AND** a "No events match the current filter" message is displayed

#### Scenario: Unknown types are ignored
- **WHEN** a client requests `/fragments/events?filter=kafka,bogus,command`
- **THEN** the response contains only events of type `KAFKA` and `COMMAND`
- **AND** no error is returned

### Requirement: Individual type chips with server-computed toggle URLs
The event panel SHALL render one chip per known event type. Each chip SHALL be styled as active (`chip-assist` class) when its type is in the current filter set, and plain when inactive.

Each chip SHALL carry an `hx-get` URL that represents the current active set with that chip's type toggled (added if absent, removed if present). Clicking a chip SHALL swap the event panel via HTMX without a full page reload.

The chips SHALL use human-friendly labels: Kafka, Command, Pending, Resolved, Sensor, REST, State, MQTT, Event.

#### Scenario: Clicking an inactive type chip adds it to the filter
- **WHEN** the active filter is `kafka,command` and the operator clicks the "State" chip
- **THEN** the event panel re-renders with filter `kafka,command,state`
- **AND** the State chip becomes active

#### Scenario: Clicking an active type chip removes it from the filter
- **WHEN** the active filter is `kafka,command,state` and the operator clicks the "State" chip
- **THEN** the event panel re-renders with filter `kafka,command`
- **AND** the State chip becomes inactive

### Requirement: Preset shortcuts
The event panel SHALL render preset shortcut chips (All, Process, None) in a separate row above the individual type chips. Clicking a preset SHALL set the active types to the corresponding predefined set:

- **All**: all 9 known event types
- **Process**: `KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`
- **None**: empty set (no types)

After clicking a preset, individual type chips SHALL still be togglable.

#### Scenario: Clicking All preset activates all types
- **WHEN** the operator clicks the "All" preset
- **THEN** the event panel re-renders with all 9 event types active
- **AND** all individual type chips show as active

#### Scenario: Clicking None preset clears all types
- **WHEN** the operator clicks the "None" preset
- **THEN** the event panel re-renders with no events shown
- **AND** all individual type chips show as inactive
- **AND** a "No events match the current filter" message is displayed

#### Scenario: Clicking Process preset sets process types
- **WHEN** the operator clicks the "Process" preset
- **THEN** the event panel re-renders with exactly `KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST` active

### Requirement: SSE reconnects with updated filter
When the event panel is swapped after a filter change, the page SHALL reconnect the SSE stream with the new filter parameter so live updates reflect the operator's current filter selection.

The event panel SHALL expose the active types in a `data-active-types` attribute (comma-separated lowercase) for the SSE reconnect script to read.

#### Scenario: Filter change triggers SSE reconnect
- **WHEN** the operator toggles a type chip causing the event panel to swap
- **THEN** the SSE connection closes and reconnects to `/sse/status?filter=<new-types>`
- **AND** subsequent live updates render only events matching the new filter
