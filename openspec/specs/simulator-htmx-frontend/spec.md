# Simulator htmx Frontend

Version: v1

## Purpose
Deliver a server-rendered htmx frontend for the simulated factory, streaming live state updates over SSE.
## Requirements
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

### Requirement: htmx-driven page shell
The service SHALL serve a `base.html` page at `GET /` that loads htmx and the SSE extension from CDN and uses `hx-get` with `hx-trigger="load"` to fetch each panel fragment on initial page load.

The page shell SHALL treat the event-panel filter mode as a request parameter. The selected mode SHALL default to `full`, SHALL accept `process` when explicitly requested, and SHALL be threaded into both the event-panel fragment request and the existing page-wide SSE connection used for live updates.

When the operator changes filter mode without reloading the page, the frontend SHALL update the current browser URL using `history.replaceState` and SHALL reconnect the existing page-wide SSE stream with the selected `filter` parameter so live updates continue in the same mode.

#### Scenario: Browser loads the simulator UI
- **WHEN** a browser navigates to `GET /`
- **THEN** the page shell is returned
- **AND** all panel fragments are fetched and injected via htmx on load
- **AND** the SSE connection is established for live updates
- **AND** the event panel is requested with the default `full` filter mode

#### Scenario: Browser loads a process-filtered simulator UI
- **WHEN** a browser navigates to `GET /?filter=process`
- **THEN** the page shell is returned with the event-panel fragment request targeting process mode
- **AND** the SSE connection is established with the same process filter mode
- **AND** subsequent event-panel updates use that same selected mode until the operator changes it

#### Scenario: Operator changes filter mode in place
- **WHEN** the operator changes the event-panel filter without reloading the full page
- **THEN** the current browser URL is replaced with the selected `?filter=` value rather than pushing a new history entry
- **AND** the existing page-wide SSE connection is re-established with that same selected filter mode
- **AND** subsequent SSE updates for the event panel use the new selected mode

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

### Requirement: Slider sensor preview swaps are local and ephemeral
The simulator HTMX frontend SHALL treat color-sensor and distance-sensor preview state as local draft UI state only. A previewed draft SHALL be replaceable by the next committed twin-panel rerender.

#### Scenario: SSE refresh discards an unsubmitted draft
- **WHEN** a color-sensor or distance-sensor control is showing preview-only values and an SSE twin-panel refresh arrives before `Apply`
- **THEN** the committed twin-panel fragment replaces the previewed draft
- **AND** the operator sees the last committed sensor state

