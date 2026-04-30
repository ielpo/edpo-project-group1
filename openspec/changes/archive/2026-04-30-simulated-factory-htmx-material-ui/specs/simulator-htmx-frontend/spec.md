# Simulator htmx Frontend

Version: v1

## ADDED Requirements

### Requirement: Server-rendered HTML fragment endpoints
The service SHALL expose `GET /fragments/{panel}` endpoints for each UI panel — `status`, `presets`, `sensors`, `events`, and `pending` — returning rendered HTML fragments compatible with htmx `hx-swap`.

#### Scenario: Client requests a panel fragment
- **WHEN** a client sends `GET /fragments/presets`
- **THEN** the service returns an HTML fragment containing the current preset list
- **AND** the fragment can be injected directly into the page without further transformation

### Requirement: Server-Sent Events live update stream
The service SHALL expose `GET /sse/status` as a `text/event-stream` endpoint. On each simulator state change, it SHALL push out-of-band HTML fragments for all affected panels.

#### Scenario: Preset run triggers a live UI update
- **WHEN** a preset run starts and the simulation state changes
- **THEN** the SSE stream emits an event containing updated HTML for the status panel and relevant panels
- **AND** a connected htmx client with `hx-ext="sse"` automatically swaps those fragments into the page

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

### Requirement: Sensor form submits via htmx
The service SHALL accept sensor updates via `hx-put` on the sensor card form and SHALL return an updated HTML fragment for the affected sensor card so only that card is replaced.

#### Scenario: Operator updates a sensor value
- **WHEN** an operator submits a sensor edit form in the UI
- **THEN** the service processes the update and returns an updated HTML fragment for that sensor card
- **AND** only the affected card is replaced in the page, not the full sensor panel

### Requirement: Material Design 3 visual styling
The service UI SHALL follow Material Design 3 guidelines using custom CSS with MD3 design tokens (color roles, elevation, typescale) as CSS custom properties. It SHALL use the Roboto typeface and SHALL NOT depend on any third-party component library.

#### Scenario: UI renders with MD3 color roles
- **WHEN** the simulator UI is opened
- **THEN** the page uses the MD3 color role system (primary, surface, surface-variant, error, outline) via CSS custom properties
- **AND** elevation levels are expressed via surface tint overlays per the MD3 specification
- **AND** the Roboto typeface is applied
