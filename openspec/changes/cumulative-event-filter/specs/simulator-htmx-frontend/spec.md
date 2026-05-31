# Simulator htmx Frontend — Delta

## MODIFIED Requirements

### Requirement: Event-panel filter toggles
The simulator events panel SHALL provide cumulative per-type filter chips and preset shortcuts (All, Process, None) for composing the visible event set.

The selected filter SHALL control which events the server renders without removing any entries from backend full history. Chip interactions SHALL toggle individual event types in the active filter set via server-side HTMX round-trips rather than relying on client-side hiding.

#### Scenario: Operator composes a custom filter
- **WHEN** the operator toggles individual type chips to build a custom filter (e.g. Kafka + Sensor + State)
- **THEN** the resulting event-panel request carries a `filter` parameter listing the selected types as a comma-separated lowercase string
- **AND** the returned panel shows only events matching the selected types
- **AND** the full simulator page is not reloaded to apply the filter change
- **AND** live SSE refreshes continue rendering the event panel with the same filter until the filter changes

#### Scenario: Operator uses a preset to bulk-set types
- **WHEN** the operator clicks the "Process" preset chip
- **THEN** the resulting event-panel request carries `filter=kafka,command,pending_action,action_resolved,sensor_request`
- **AND** the returned panel shows only process-relevant event types
- **AND** individual type chips reflect the preset's selection and remain independently togglable

## REMOVED Requirements

### Requirement: Event-panel filter toggles (binary mode)
**Reason**: Replaced by cumulative per-type filter chips. The binary `Full log` / `Process view` toggle is superseded by the more flexible preset shortcuts and individual type chips.
**Migration**: Use `?filter=kafka,command,pending_action,action_resolved,sensor_request,rest,state,mqtt,event` for "full" or `?filter=kafka,command,pending_action,action_resolved,sensor_request` for "process".
