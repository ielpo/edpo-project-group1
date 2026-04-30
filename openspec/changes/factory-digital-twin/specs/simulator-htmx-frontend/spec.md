## REMOVED Requirements

### Requirement: Server-rendered HTML fragment endpoints (partial removal)
**Reason**: The `sensors` fragment panel is replaced by the `twin` fragment. The `GET /fragments/sensors` endpoint and its template (`sensors.html`, `_sensor_card.html`) are removed.
**Migration**: Use `GET /fragments/twin` to retrieve the combined factory twin panel which includes all sensor controls inline.

## MODIFIED Requirements

### Requirement: Server-rendered HTML fragment endpoints
The service SHALL expose `GET /fragments/{panel}` endpoints for each UI panel — `status`, `presets`, `twin`, `events`, and `pending` — returning rendered HTML fragments compatible with htmx `hx-swap`.

The `presets` fragment endpoint SHALL accept and use the current simulation state when rendering, so that active step highlighting can be computed server-side.

The `twin` fragment endpoint SHALL accept and use the current simulation state, all sensor configurations, and the cached inventory grid when rendering the block diagram.

#### Scenario: Client requests a panel fragment
- **WHEN** a client sends `GET /fragments/presets`
- **THEN** the service returns an HTML fragment containing the current preset list
- **AND** the fragment can be injected directly into the page without further transformation
- **AND** if a preset is currently running, the fragment SHALL include a step pipeline on that preset's card

#### Scenario: Presets fragment reflects running state
- **WHEN** a preset is running and a client sends `GET /fragments/presets`
- **THEN** the fragment SHALL render a step pipeline on the running preset's card with completed/active/pending step nodes
- **AND** no other preset card SHALL contain a step pipeline

#### Scenario: Client requests the twin fragment
- **WHEN** a client sends `GET /fragments/twin`
- **THEN** the service returns an HTML fragment containing the factory block diagram
- **AND** the fragment includes sensor controls for all configured sensors

### Requirement: Server-Sent Events live update stream
The service SHALL expose `GET /sse/status` as a `text/event-stream` endpoint. On each simulator state change, it SHALL push out-of-band HTML fragments for all affected panels: `status`, `presets`, `twin`, `events`, and `pending`.

#### Scenario: Preset run triggers a live UI update
- **WHEN** a preset run starts and the simulation state changes
- **THEN** the SSE stream emits an event containing updated HTML for the status panel and the twin panel (among others)
- **AND** a connected htmx client with `hx-ext="sse"` automatically swaps those fragments into the page

#### Scenario: SSE client reconnects after disconnect
- **WHEN** an SSE client loses the connection and reconnects
- **THEN** the service accepts the new connection
- **AND** the client re-renders with current state

## ADDED Requirements

### Requirement: Sensor form submits via htmx (inline in twin)
The service SHALL accept sensor updates via `hx-put` on sensor forms embedded within the twin panel. It SHALL return an updated HTML fragment for the affected sensor zone so only that zone is replaced.

#### Scenario: Operator updates a sensor value from twin
- **WHEN** an operator submits a sensor edit form inside the twin panel
- **THEN** the service processes the update and returns an updated HTML fragment for that sensor's zone
- **AND** only the affected sensor zone is replaced in the page, not the full twin panel
