## MODIFIED Requirements

### Requirement: Server-rendered HTML fragment endpoints
The service SHALL expose `GET /fragments/{panel}` endpoints for each UI panel — `status`, `presets`, `twin`, `events`, and `pending` — returning rendered HTML fragments compatible with htmx `hx-swap`.

The fragment endpoints SHALL obtain their panel view models from one shared runtime snapshot source so each render cycle uses one coherent simulator read model.

The `presets` fragment endpoint SHALL accept and use the current simulation state when rendering, so that active step highlighting can be computed server-side.

The `twin` fragment endpoint SHALL accept and use the current simulation state, all sensor configurations, and the cached inventory grid when rendering the block diagram. It SHALL render manual sensor controls only, and it SHALL use the current simulation status to decide whether those controls are editable or disabled.

For color sensors, the twin fragment SHALL render a named-color selector plus three stacked RGB sliders labeled for the red, green, and blue channels. The sliders SHALL reflect the committed `raw_color` state as three integers in the inclusive range `0-255`.

For distance sensors, the twin fragment SHALL render a single slider labeled for distance. The slider SHALL reflect the committed numeric value as a floating-point number in the inclusive range `0.0-30.0`.

When the committed RGB triple exactly matches the canonical value for `RED`, `GREEN`, `BLUE`, or `YELLOW`, the selector SHALL render that preset as selected. Otherwise the selector SHALL render `(none)` as selected.

The service SHALL expose `GET /sse/status` as a `text/event-stream` endpoint. On each simulator state change, it SHALL push out-of-band HTML fragments for all affected panels, and those fragments SHALL be rendered from the same shared runtime snapshot source used by the fragment endpoints.

#### Scenario: Client requests a panel fragment
- **WHEN** a client sends `GET /fragments/presets`
- **THEN** the service returns an HTML fragment containing the current preset list
- **AND** the fragment can be injected directly into the page without further transformation
- **AND** if a preset is currently running, the fragment SHALL include a step pipeline on that preset's card

#### Scenario: Client requests the twin fragment while idle
- **WHEN** a client sends `GET /fragments/twin` while no preset is running
- **THEN** the service returns an HTML fragment containing the factory block diagram
- **AND** the fragment includes editable color preset selectors and three RGB sliders for each configured color sensor
- **AND** the fragment includes editable range sliders for each configured distance sensor
- **AND** the fragment includes editable manual-value controls for all other configured sensors without scripted-value editors or mode toggles

#### Scenario: Client requests the twin fragment during a preset run
- **WHEN** a client sends `GET /fragments/twin` while a preset is running
- **THEN** the service returns an HTML fragment containing the factory block diagram
- **AND** the fragment shows the live current sensor values in disabled, read-only controls

#### Scenario: Twin fragment renders unnamed RGB values
- **WHEN** a color sensor has a committed `raw_color` value that does not exactly match a canonical named color
- **THEN** the twin fragment renders the RGB sliders with that committed triple
- **AND** the named-color selector renders `(none)` as selected

#### Scenario: Twin fragment renders committed distance values
- **WHEN** a distance sensor has a committed value of `12.5`
- **THEN** the twin fragment renders the distance slider at `12.5`
- **AND** the control exposes the distance sensor as a slider rather than a numeric text box

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

### Requirement: Sensor update relies on SSE for operator visual refresh
The simulator HTMX frontend SHALL rely on the SSE out-of-band swap stream for reflecting committed sensor configuration changes and lock-state changes in the operator UI. The persistence form SHALL use `hx-swap="none"` and SHALL NOT depend on the PUT response body for visual updates.

Color-sensor and distance-sensor preview interactions SHALL use a localized HTML fragment swap that updates only the touched sensor control and SHALL NOT persist simulator state until the operator presses `Apply`.

The previewed slider-based sensor control SHALL expose a visible unsaved-state marker on the `Apply` action after a preview-only interaction.

#### Scenario: Operator previews a named color without persisting it
- **WHEN** an operator changes the named-color selector for a color sensor while no preset is running
- **THEN** the UI sends a preview request for only that color-sensor control
- **AND** the response swaps only the touched color-sensor fragment
- **AND** the updated fragment shows the canonical RGB slider values and an unsaved-state marker
- **AND** the simulator's committed sensor state remains unchanged until `Apply`

#### Scenario: Operator previews a slider change without persisting it
- **WHEN** an operator releases one of the RGB sliders for a color sensor while no preset is running
- **THEN** the UI sends a preview request for only that color-sensor control
- **AND** the response swaps only the touched color-sensor fragment
- **AND** the updated fragment reflects the normalized draft RGB values and current named-color selection
- **AND** the simulator's committed sensor state remains unchanged until `Apply`

#### Scenario: Operator previews a distance slider change without persisting it
- **WHEN** an operator releases the slider for a distance sensor while no preset is running
- **THEN** the UI sends a preview request for only that distance-sensor control
- **AND** the response swaps only the touched distance-sensor fragment
- **AND** the updated fragment reflects the normalized draft distance value in the inclusive range `0.0-30.0`
- **AND** the simulator's committed sensor state remains unchanged until `Apply`

#### Scenario: Operator submits sensor form and sees updated twin while idle
- **WHEN** an operator submits a manual sensor edit form in the twin panel while no preset is running
- **THEN** the form sends `PUT /api/config/sensors/{id}` with `hx-swap="none"`
- **AND** the SSE stream emits an updated twin panel fragment with `hx-swap-oob="true"`
- **AND** the twin panel reflects the new committed sensor configuration without using the PUT response body

#### Scenario: Preset state change locks or unlocks sensor controls
- **WHEN** the simulator transitions between idle and running preset states
- **THEN** the SSE stream emits an updated twin panel fragment reflecting the new disabled or enabled sensor controls
- **AND** the operator UI does not derive sensor lock state locally in browser JavaScript

## ADDED Requirements

### Requirement: Slider sensor preview swaps are local and ephemeral
The simulator HTMX frontend SHALL treat color-sensor and distance-sensor preview state as local draft UI state only. A previewed draft SHALL be replaceable by the next committed twin-panel rerender.

#### Scenario: SSE refresh discards an unsubmitted draft
- **WHEN** a color-sensor or distance-sensor control is showing preview-only values and an SSE twin-panel refresh arrives before `Apply`
- **THEN** the committed twin-panel fragment replaces the previewed draft
- **AND** the operator sees the last committed sensor state