## MODIFIED Requirements

### Requirement: Sensor controls inline in twin panel
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
