# Simulator htmx Frontend — Delta

## MODIFIED Requirements

### Requirement: Server-rendered HTML fragment endpoints
The service SHALL expose `GET /fragments/{panel}` endpoints for each UI panel — `status`, `presets`, `sensors`, `events`, and `pending` — returning rendered HTML fragments compatible with htmx `hx-swap`.

The `presets` fragment endpoint SHALL accept and use the current simulation state when rendering, so that active step highlighting can be computed server-side.

#### Scenario: Client requests a panel fragment
- **WHEN** a client sends `GET /fragments/presets`
- **THEN** the service returns an HTML fragment containing the current preset list
- **AND** the fragment can be injected directly into the page without further transformation
- **AND** if a preset is currently running, the fragment SHALL include a step pipeline on that preset's card

#### Scenario: Presets fragment reflects running state
- **WHEN** a preset is running and a client sends `GET /fragments/presets`
- **THEN** the fragment SHALL render a step pipeline on the running preset's card with completed/active/pending step nodes
- **AND** no other preset card SHALL contain a step pipeline
