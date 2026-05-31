## MODIFIED Requirements

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