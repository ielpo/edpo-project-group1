# Factory Twin Diagram

Version: v1

## Purpose
Render the factory state as an interactive block-diagram twin panel so operators can observe and configure sensors inline.
## Requirements
### Requirement: Factory twin panel rendered as block diagram
The service SHALL expose `GET /fragments/twin` returning an HTML fragment that renders the factory as a CSS-grid block diagram with six named zones: Inventory Grid, Conveyor Belt, Distance Sensor, Color Sensor, Robot (Dobot), and Assembly Area.

#### Scenario: Client requests the twin fragment
- **WHEN** a client sends `GET /fragments/twin`
- **THEN** the service returns an HTML fragment containing all six factory zones
- **AND** each zone shows its current state (sensor values, robot position, block location)
- **AND** the fragment is compatible with htmx `hx-swap="outerHTML"`

#### Scenario: Twin fragment is included in SSE OOB stream
- **WHEN** the simulation state changes
- **THEN** the SSE stream SHALL include an updated `twin` fragment as an out-of-band swap
- **AND** the browser replaces the previous twin panel without a page reload

### Requirement: Block location indicator
The twin panel SHALL derive the current block location from `currentStepName` and display a location badge in the appropriate factory zone.

#### Scenario: Block in inventory (no active step)
- **WHEN** `currentStepName` is null or `order-received`
- **THEN** the Inventory Grid zone shows reserved cells with a dashed outline
- **AND** no location badge appears in the Conveyor or Assembly zones

#### Scenario: Block on conveyor
- **WHEN** `currentStepName` is `pickup`
- **THEN** the Conveyor Belt zone SHALL display a "ON CONVEYOR" location badge
- **AND** the Inventory and Assembly zones SHALL NOT display a location badge

#### Scenario: Block at pickup zone
- **WHEN** `currentStepName` is `color-check`
- **THEN** the Conveyor Belt zone SHALL display an "AT PICKUP ZONE" location badge

#### Scenario: Block with robot or in assembly
- **WHEN** `currentStepName` is `place` or `reject`
- **THEN** the Assembly Area zone SHALL display a "BEING PLACED" or "BEING REJECTED" location badge respectively

#### Scenario: Unknown step name
- **WHEN** `currentStepName` is set to a value not in the defined mapping
- **THEN** the Conveyor Belt zone SHALL display an "IN PROGRESS" badge
- **AND** the service SHALL NOT error

### Requirement: Inline typed sensor controls in twin
The twin panel SHALL render sensor configuration controls directly within the appropriate sensor zone. Color sensor zones SHALL render a mode selector, a color value selector with CSS swatch, a raw RGB input, and a submit button. Distance/IR sensor zones SHALL render a mode selector, a value input appropriate to the sensor type, and a submit button.

Sensor forms SHALL submit via `hx-put="/api/config/sensors/{id}"` with `hx-swap="none"` and `hx-ext="json-enc"`. The operator visual refresh SHALL occur through the SSE out-of-band swap stream, not through the PUT response body.

#### Scenario: Color sensor control renders selectors and raw input
- **WHEN** the twin fragment is rendered and a color sensor exists
- **THEN** the zone SHALL render a `<select>` for mode (fixed/scripted), a `<select>` for color value (RED/GREEN/BLUE/YELLOW) with CSS color swatch, and a raw RGB input
- **AND** a comma-list text input for scripted_values SHALL be shown when mode is scripted

#### Scenario: IR sensor control renders a boolean dropdown
- **WHEN** a sensor ID matches the prefix `ir-*`
- **THEN** the zone SHALL render a `<select>` for mode (fixed/scripted) and a `<select>` for value (true/false)

#### Scenario: Sensor update submitted from twin
- **WHEN** an operator submits the sensor form inside the twin panel
- **THEN** the service processes the `PUT /api/config/sensors/{id}` request
- **AND** the twin panel is refreshed via the SSE out-of-band swap stream
- **AND** the form does not use the PUT response body for visual updates

### Requirement: Robot state displayed read-only in twin
The twin panel SHALL display the left Dobot's runtime state (position x/y/z/r, speed, suction enabled, conveyor direction) in the Robot zone as read-only values.

#### Scenario: Robot state shown during active preset
- **WHEN** a preset is running and the twin fragment is rendered
- **THEN** the Robot zone SHALL show the current `DobotRuntimeState` for `dobots.left`
- **AND** no editable controls SHALL appear in the Robot zone

