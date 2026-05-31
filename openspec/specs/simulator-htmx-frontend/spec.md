# Simulator htmx Frontend

Version: v1

## Purpose
Deliver a server-rendered htmx frontend for the simulated factory, streaming live state updates over SSE.
## Requirements
### Requirement: Server-rendered HTML fragment endpoints
The service SHALL expose `GET /fragments/{panel}` endpoints for each UI panel — `status`, `presets`, `twin`, `events`, and `pending` — returning rendered HTML fragments compatible with htmx `hx-swap`.

The fragment endpoints SHALL obtain their panel view models from one shared runtime snapshot source so each render cycle uses one coherent simulator read model.

The `presets` fragment endpoint SHALL accept and use the current simulation state when rendering, so that active step highlighting can be computed server-side.

The `twin` fragment endpoint SHALL accept and use the current simulation state, all sensor configurations, and the cached inventory grid when rendering the block diagram.

The service SHALL expose `GET /sse/status` as a `text/event-stream` endpoint. On each simulator state change, it SHALL push out-of-band HTML fragments for all affected panels, and those fragments SHALL be rendered from the same shared runtime snapshot source used by the fragment endpoints.

#### Scenario: Client requests a panel fragment
- **WHEN** a client sends `GET /fragments/presets`
- **THEN** the service returns an HTML fragment containing the current preset list
- **AND** the fragment can be injected directly into the page without further transformation
- **AND** if a preset is currently running, the fragment SHALL include a step pipeline on that preset's card

#### Scenario: Client requests the twin fragment
- **WHEN** a client sends `GET /fragments/twin`
- **THEN** the service returns an HTML fragment containing the factory block diagram
- **AND** the fragment includes sensor controls for all configured sensors

#### Scenario: Preset run triggers a live UI update: `status`, `presets`, `twin`, `events`, and `pending`
- **WHEN** a preset run starts and the simulation state changes
- **THEN** the SSE stream emits an event containing updated HTML for the status panel and the twin panel (among others)
- **AND** a connected htmx client with `hx-ext="sse"` automatically swaps those fragments into the page

#### Scenario: Fragment and SSE rendering share one read model
- **WHEN** the service renders a fragment endpoint and later renders the SSE update for the same simulator state
- **THEN** both renders use the same shared runtime snapshot source
- **AND** the rendered panels do not depend on duplicated ad hoc view-model assembly in separate handlers

#### Scenario: SSE client reconnects after disconnect
- **WHEN** an SSE client loses the connection and reconnects
- **THEN** the service accepts the new connection
- **AND** the client re-renders with current state

### Requirement: htmx-driven page shell
The service SHALL serve a `base.html` page at `GET /` that loads htmx and the SSE extension from CDN and uses `hx-get` with `hx-trigger="load"` to fetch each panel fragment on initial page load.

#### Scenario: Browser loads the simulator UI
- **WHEN** a browser navigates to `GET /`
- **THEN** the page shell is returned
- **AND** all panel fragments are fetched and injected via htmx on load
- **AND** the SSE connection is established for live updates

### Requirement: Material Design 3 visual styling
The service UI SHALL follow Material Design 3 guidelines using custom CSS with MD3 design tokens (color roles, elevation, typescale) as CSS custom properties. It SHALL use the Roboto typeface and SHALL NOT depend on any third-party component library.

The MD3 color role tokens SHALL be sourced from the project's five-color palette as defined in the `simulator-ui-color-palette` capability. The default MD3 purple baseline SHALL NOT be used.

#### Scenario: UI renders with MD3 color roles
- **WHEN** the simulator UI is opened
- **THEN** the page uses the MD3 color role system (primary, surface, surface-variant, error, tertiary, outline) via CSS custom properties
- **AND** all color tokens resolve to values derived from the project palette (glaucous, muted teal, light coral, alabaster grey, jet-black)
- **AND** elevation levels are expressed via surface tint overlays per the MD3 specification
- **AND** the Roboto typeface is applied

### Requirement: Event-panel filter toggles
The simulator events panel SHALL provide explicit filter toggles for `Full log` and `Process view`.

The selected filter SHALL control which events are rendered without removing any entries from backend full history.

#### Scenario: Operator switches to process view
- **WHEN** the operator selects `Process view` in the events panel
- **THEN** the panel shows only process-relevant event types (`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`)
- **AND** non-process events (for example `REST`, `STATE`, `MQTT`) are hidden from this view

#### Scenario: Operator switches back to full log
- **WHEN** the operator selects `Full log` in the events panel
- **THEN** the panel shows the complete chronological event stream including `MQTT` and other debugging signals

### Requirement: Human-readable process event rendering
In process view, the events panel SHALL render robot command events in a human-readable summary format so operators can quickly follow robot behavior.

The rendering SHALL include action-oriented descriptions for common command types such as move target coordinates, suction cup state, and conveyor movement.

#### Scenario: Move and suction commands are readable
- **WHEN** a command event includes move and suction-cup operations
- **THEN** the panel displays readable command summaries (for example move target coordinates and suction ON/OFF)
- **AND** operators can still inspect raw payload details when needed

### Requirement: Sensor request visibility in process view
The events panel SHALL display `SENSOR_REQUEST` events in process view with clear endpoint context.

#### Scenario: Sensor request appears in process log
- **WHEN** a `SENSOR_REQUEST` event is recorded for color or IR endpoint access
- **THEN** the process view includes the event in chronological order
- **AND** the rendered entry identifies the sensor endpoint that was requested

### Requirement: Sensor update relies on SSE for operator visual refresh
The simulator HTMX frontend SHALL rely exclusively on the SSE out-of-band swap stream for reflecting sensor configuration changes in the operator UI. The sensor form SHALL use `hx-swap="none"` and SHALL NOT depend on the PUT response body for visual updates.

#### Scenario: Operator submits sensor form and sees updated twin
- **WHEN** an operator submits a sensor edit form in the twin panel
- **THEN** the form sends `PUT /api/config/sensors/{id}` with `hx-swap="none"`
- **AND** the SSE stream emits an updated twin panel fragment with `hx-swap-oob="true"`
- **AND** the twin panel reflects the new sensor configuration without using the PUT response body

